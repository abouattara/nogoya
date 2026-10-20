"""Les dix garanties attendues du système d'import.

Aucun test ne touche le réseau : les adaptateurs sont remplacés par des
doubles, et la source « fichier » lit un CSV écrit dans un dossier
temporaire. Un test qui dépendrait d'un site tiers serait rouge le jour où
ce site change une virgule — et ne dirait plus rien de notre code.
"""
import shutil
import tempfile
from datetime import datetime, timedelta
from datetime import timezone as dt_timezone
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.catalog.models import Category, Product
from apps.sourcing.adapters.base import AdapterError, RawListing, SourceAdapter
from apps.sourcing.models import ListingImport, ListingSource
from apps.sourcing.net import UnsafeUrl, assert_public_url
from apps.sourcing.services import import_service_supplier, run_import

User = get_user_model()
IMPORT_DIR = tempfile.mkdtemp(prefix="nogoya_imports_")


def make_source(**overrides):
    defaults = {
        "name": "Agence Exemple",
        "slug": "agence-exemple",
        "kind": ListingSource.Kind.API,
        "is_active": True,
        "authorization_note": "Contrat signé le 2026-10-01, import des annonces autorisé.",
        "config": {"adapter": "stub"},
    }
    return ListingSource.objects.create(**{**defaults, **overrides})


def listing(**overrides):
    defaults = {
        "external_id": "A-1",
        "original_url": "https://exemple.test/annonces/a-1",
        "title": "Appartement 2 chambres à Ouaga 2000",
        "description": "Appartement meublé, cuisine équipée.",
        "price_text": "150 000 FCFA / mois",
        "city": "Ouagadougou",
        "category_hint": "Appartements",
        "collected_at": datetime(2026, 10, 20, tzinfo=dt_timezone.utc),
        "raw": {"id": "A-1"},
    }
    return RawListing(**{**defaults, **overrides})


class StubAdapter(SourceAdapter):
    """Adaptateur de test : rend ce qu'on lui a donné, ou lève."""

    key = "stub"
    items = []
    failure = None

    def fetch(self):
        if StubAdapter.failure:
            raise AdapterError(StubAdapter.failure)
        return iter(StubAdapter.items)


def with_stub(items=None, failure=None):
    StubAdapter.items = items or []
    StubAdapter.failure = failure
    return patch("apps.sourcing.services.get_adapter", lambda source: StubAdapter(source))


@override_settings(SOURCING_IMPORT_DIR=IMPORT_DIR)
class ImportPipelineTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(IMPORT_DIR, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.logements = Category.objects.create(name="Logements")
        self.appartements = Category.objects.create(name="Appartements", parent=self.logements)
        self.source = make_source()

    # 1 — importation d'une annonce valide
    def test_valid_listing_becomes_a_draft_never_a_publication(self):
        with with_stub([listing()]):
            report = run_import(self.source)

        self.assertEqual(report.created, 1, report.errors)
        product = Product.objects.get()
        self.assertEqual(product.title, "Appartement 2 chambres à Ouaga 2000")
        self.assertEqual(product.price, 150_000)
        self.assertEqual(product.currency, "XOF")
        self.assertEqual(product.rental_period, Product.RentalPeriod.MONTH)
        self.assertEqual(product.category, self.appartements)
        # Le point central : rien n'est publié par un programme.
        self.assertEqual(product.status, Product.Status.DRAFT)
        self.assertFalse(product.is_active)

    def test_nothing_is_invented_when_the_source_is_silent(self):
        """Un champ absent reste absent — jamais comblé par une valeur plausible."""
        with with_stub([listing(price_text=None, city=None)]):
            report = run_import(self.source)

        self.assertEqual(report.created, 0)
        self.assertEqual(report.invalid, 1)
        record = ListingImport.objects.get()
        self.assertIsNone(record.normalized["price"])
        self.assertEqual(record.normalized["city"], "")
        self.assertIn("Prix absent", record.error_message)
        self.assertIn("Ville absente", record.error_message)

    # 2 — rejet d'une annonce invalide
    def test_invalid_listing_is_held_with_its_reason(self):
        with with_stub([listing(title="Maison", price_text="0 FCFA")]):
            run_import(self.source)

        record = ListingImport.objects.get()
        self.assertEqual(record.status, ListingImport.Status.INVALID)
        self.assertFalse(Product.objects.exists())
        self.assertIn("Titre absent ou trop court", record.error_message)

    # 3 — détection des doublons
    def test_same_listing_twice_updates_instead_of_duplicating(self):
        with with_stub([listing()]):
            run_import(self.source)
        with with_stub([listing(price_text="160 000 FCFA / mois")]):
            report = run_import(self.source)

        self.assertEqual(report.updated, 1)
        self.assertEqual(Product.objects.count(), 1)
        self.assertEqual(ListingImport.objects.count(), 1)
        self.assertEqual(Product.objects.get().price, 160_000)

    def test_a_similar_listing_from_another_source_is_flagged_not_created(self):
        with with_stub([listing()]):
            run_import(self.source)

        other = make_source(name="Autre source", slug="autre-source")
        with with_stub([listing(external_id="B-9", original_url="https://autre.test/9")]):
            report = run_import(other)

        self.assertEqual(report.duplicates, 1)
        self.assertEqual(report.created, 0)
        # Toujours une seule annonce, et la trace du rapprochement.
        self.assertEqual(Product.objects.count(), 1)
        flagged = ListingImport.objects.get(source=other)
        self.assertEqual(flagged.status, ListingImport.Status.DUPLICATE)
        self.assertIn("Rapprochement", flagged.error_message)

    def test_two_different_flats_at_different_prices_are_both_kept(self):
        """Le titre seul ne décide de rien : deux biens voisins restent deux biens."""
        with with_stub([
            listing(external_id="A-1", original_url="https://exemple.test/1"),
            listing(
                external_id="A-2",
                original_url="https://exemple.test/2",
                price_text="320 000 FCFA / mois",
            ),
        ]):
            report = run_import(self.source)

        self.assertEqual(report.created, 2, report.errors)
        self.assertEqual(Product.objects.count(), 2)

    # 4 — source indisponible
    def test_a_broken_source_reports_failure_without_raising(self):
        with with_stub(failure="Flux injoignable"):
            report = run_import(self.source)

        self.assertEqual(report.status, ListingSource.RunStatus.FAILED)
        self.assertIn("Flux injoignable", report.errors[0])
        self.source.refresh_from_db()
        self.assertEqual(self.source.last_run_status, ListingSource.RunStatus.FAILED)

    def test_a_failed_run_never_expires_the_existing_catalogue(self):
        """Une panne de la source ne doit pas vider le catalogue."""
        with with_stub([listing()]):
            run_import(self.source)
        with with_stub(failure="502 Bad Gateway"):
            run_import(self.source)

        self.assertEqual(Product.objects.get().status, Product.Status.DRAFT)
        self.assertEqual(ListingImport.objects.get().status, ListingImport.Status.IMPORTED)

    # 9 — annonces expirées
    def test_a_listing_that_vanished_is_marked_expired(self):
        with with_stub([listing()]):
            run_import(self.source)
        with with_stub([]):
            run_import(self.source)

        self.assertEqual(ListingImport.objects.get().status, ListingImport.Status.EXPIRED)
        product = Product.objects.get()
        self.assertEqual(product.status, Product.Status.EXPIRED)
        self.assertFalse(product.is_active)

    def test_a_listing_that_reappears_returns_to_the_review_queue(self):
        with with_stub([listing()]):
            run_import(self.source)
        with with_stub([]):
            run_import(self.source)
        with with_stub([listing()]):
            run_import(self.source)

        self.assertEqual(Product.objects.get().status, Product.Status.DRAFT)

    def test_a_rejected_listing_is_not_resurrected_by_the_next_run(self):
        with with_stub([listing()]):
            run_import(self.source)
        Product.objects.update(status=Product.Status.REJECTED)

        with with_stub([listing(price_text="200 000 FCFA / mois")]):
            run_import(self.source)

        self.assertEqual(Product.objects.get().status, Product.Status.REJECTED)

    # 5 — provenance
    def test_imported_listings_carry_their_provenance_and_never_a_fake_owner(self):
        with with_stub([listing()]):
            run_import(self.source)

        product = Product.objects.get()
        self.assertEqual(product.provenance, Product.Provenance.EXTERNAL_REFERENCE)
        self.assertEqual(product.source, self.source)
        self.assertEqual(product.source_url, "https://exemple.test/annonces/a-1")
        self.assertTrue(product.is_externally_sourced)

        # Le compte porteur est un compte de service, inactif et sans mot de passe.
        service = import_service_supplier()
        self.assertEqual(product.supplier, service)
        self.assertFalse(service.user.is_active)
        self.assertFalse(service.user.has_usable_password())

    def test_a_partner_file_is_marked_as_a_partner_not_an_external_reference(self):
        partner = make_source(
            name="Partenaire CSV", slug="partenaire-csv",
            kind=ListingSource.Kind.FILE, config={"adapter": "stub"},
        )
        with with_stub([listing(original_url="")]):
            run_import(partner)

        self.assertEqual(
            Product.objects.get().provenance, Product.Provenance.AUTHORIZED_PARTNER
        )

    # photos et coordonnées : rien n'est repris sans autorisation
    def test_images_are_ignored_unless_the_source_allows_their_reuse(self):
        with with_stub([listing(image_urls=["https://exemple.test/p.jpg"])]):
            run_import(self.source)
        self.assertEqual(ListingImport.objects.get().normalized["image_urls"], [])

        self.source.allows_image_reuse = True
        self.source.save()
        with with_stub([listing(image_urls=["https://exemple.test/p.jpg"])]):
            run_import(self.source)
        self.assertEqual(
            ListingImport.objects.get().normalized["image_urls"],
            ["https://exemple.test/p.jpg"],
        )

    def test_contact_details_are_dropped_unless_the_source_allows_them(self):
        with with_stub([listing(contact_public="+226 70 00 00 00")]):
            run_import(self.source)
        self.assertEqual(ListingImport.objects.get().normalized["contact_public"], "")

    # autorisation
    def test_a_source_cannot_be_activated_without_a_documented_authorization(self):
        with self.assertRaises(ValidationError):
            ListingSource.objects.create(
                name="Sans autorisation", slug="sans-autorisation",
                kind=ListingSource.Kind.FEED, is_active=True,
            )

    def test_an_inactive_source_is_never_queried(self):
        self.source.is_active = False
        self.source.save()
        with with_stub([listing()]):
            report = run_import(self.source)

        self.assertEqual(report.seen, 0)
        self.assertFalse(Product.objects.exists())

    # simulation
    def test_dry_run_writes_nothing(self):
        with with_stub([listing()]):
            report = run_import(self.source, dry_run=True)

        self.assertEqual(report.created, 1)
        self.assertFalse(Product.objects.exists())
        self.assertFalse(ListingImport.objects.exists())
        self.source.refresh_from_db()
        self.assertEqual(self.source.last_run_status, ListingSource.RunStatus.NEVER)

    def test_the_run_respects_the_source_ceiling(self):
        self.source.max_items_per_run = 2
        self.source.save()
        many = [
            listing(external_id=f"A-{i}", original_url=f"https://exemple.test/{i}",
                    price_text=f"{100 + i} 000 FCFA / mois")
            for i in range(10)
        ]
        with with_stub(many):
            report = run_import(self.source)

        self.assertEqual(report.seen, 2)


@override_settings(SOURCING_IMPORT_DIR=IMPORT_DIR)
class CsvAdapterTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(IMPORT_DIR, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        Category.objects.create(name="Voitures")
        Path(IMPORT_DIR).mkdir(parents=True, exist_ok=True)
        (Path(IMPORT_DIR) / "parc.csv").write_text(
            "Libelle;Loyer;Ville;Categorie\n"
            "Berline climatisee avec chauffeur;25 000 FCFA / jour;Ouagadougou;Voitures\n",
            encoding="utf-8",
        )
        self.source = make_source(
            name="Partenaire fichier", slug="partenaire-fichier",
            kind=ListingSource.Kind.FILE,
            endpoint="parc.csv",
            config={
                "adapter": "file",
                "delimiter": ";",
                "fields": {
                    "title": "Libelle", "price_text": "Loyer",
                    "city": "Ville", "category": "Categorie",
                },
            },
        )

    def test_a_partner_csv_is_imported_with_its_own_column_names(self):
        report = run_import(self.source)

        self.assertEqual(report.created, 1, report.errors)
        product = Product.objects.get()
        self.assertEqual(product.title, "Berline climatisee avec chauffeur")
        self.assertEqual(product.price, 25_000)
        self.assertEqual(product.rental_period, Product.RentalPeriod.DAY)

    def test_a_file_outside_the_import_directory_is_refused(self):
        """`endpoint` vient de l'admin : « ../../.env » ne doit pas être lisible."""
        self.source.endpoint = "../../.env"
        self.source.save()

        report = run_import(self.source)
        self.assertEqual(report.status, ListingSource.RunStatus.FAILED)
        self.assertIn("doit se trouver dans", report.errors[0])


class SsrfGuardTests(TestCase):
    def test_private_and_local_addresses_are_refused(self):
        for url in (
            "http://127.0.0.1/flux",
            "http://localhost/flux",
            "http://169.254.169.254/latest/meta-data/",
            "http://[::1]/flux",
            "file:///etc/passwd",
            "gopher://exemple.test/",
        ):
            with self.subTest(url=url):
                with self.assertRaises(UnsafeUrl):
                    assert_public_url(url)


@override_settings(SOURCING_IMPORT_DIR=IMPORT_DIR)
class CommandTests(TestCase):
    def setUp(self):
        Category.objects.create(name="Appartements")
        self.source = make_source()

    def test_the_command_refuses_an_unknown_source(self):
        with self.assertRaises(CommandError):
            call_command("import_listings", "--source", "inexistante")

    def test_the_command_imports_and_reports(self):
        from io import StringIO

        out = StringIO()
        with with_stub([listing()]):
            call_command("import_listings", "--source", self.source.slug, stdout=out)

        self.assertIn("1 créée(s)", out.getvalue())
        self.assertEqual(Product.objects.count(), 1)

    def test_raw_payloads_are_purged_after_the_retention_window(self):
        with with_stub([listing()]):
            run_import(self.source)
        ListingImport.objects.update(collected_at=timezone.now() - timedelta(days=60))

        call_command("prune_import_payloads", "--days", "30")
        self.assertEqual(ListingImport.objects.get().raw_payload, {})


@override_settings(SOURCING_IMPORT_DIR=IMPORT_DIR)
class PublicCatalogueTests(APITestCase):
    """Ce que le visiteur voit, et ce qu'il ne peut pas faire."""

    def setUp(self):
        Category.objects.create(name="Appartements")
        self.source = make_source(reference_url="https://exemple.test")
        with with_stub([listing()]):
            run_import(self.source)
        self.product = Product.objects.get()

    def _publish(self):
        self.product.status = Product.Status.APPROVED
        self.product.is_active = True
        self.product.save()

    # 9 — un brouillon n'est pas public
    def test_a_draft_import_is_invisible_to_the_public(self):
        listing_url = reverse("api:product-list")
        self.assertEqual(self.client.get(listing_url).data["count"], 0)
        detail = self.client.get(reverse("api:product-detail", args=[self.product.slug]))
        self.assertEqual(detail.status_code, status.HTTP_404_NOT_FOUND)

    # 7 — le lien vers l'annonce d'origine
    def test_a_published_external_listing_exposes_its_source_and_link(self):
        self._publish()
        data = self.client.get(reverse("api:product-detail", args=[self.product.slug])).data

        self.assertEqual(data["provenance"], Product.Provenance.EXTERNAL_REFERENCE)
        self.assertEqual(data["source_url"], "https://exemple.test/annonces/a-1")
        self.assertEqual(data["source"]["name"], "Agence Exemple")
        # Pas de fournisseur : NOGOYA ne loue pas ce bien.
        self.assertIsNone(data["supplier"])
        self.assertEqual(data["supplier_name"], "Agence Exemple")

    def test_the_service_account_is_never_presented_as_a_seller(self):
        self._publish()
        card = self.client.get(reverse("api:product-list")).data["results"][0]
        self.assertEqual(card["supplier_name"], "Agence Exemple")
        self.assertNotIn("+22600000000", str(card))

    # 8 — filtrage du catalogue
    def test_the_catalogue_can_be_filtered_by_provenance(self):
        self._publish()
        url = reverse("api:product-list")

        external = self.client.get(url, {"provenance": "external_reference"})
        self.assertEqual(external.data["count"], 1)

        owned = self.client.get(url, {"provenance": "nogoya_owner"})
        self.assertEqual(owned.data["count"], 0)

        by_source = self.client.get(url, {"source": "agence-exemple"})
        self.assertEqual(by_source.data["count"], 1)

    def test_an_expired_listing_leaves_the_public_catalogue(self):
        self._publish()
        with with_stub([]):
            run_import(self.source)

        self.assertEqual(self.client.get(reverse("api:product-list")).data["count"], 0)

    # le parcours de contact NOGOYA n'est pas proposé
    def test_contacting_an_external_listing_redirects_to_the_source(self):
        self._publish()
        visitor = User.objects.create_user(phone="+22670090001", password="pw")
        self.client.force_authenticate(visitor)

        response = self.client.post(reverse("api:product-contact", args=[self.product.slug]))
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data["source_url"], "https://exemple.test/annonces/a-1")


class AdminAccessTests(TestCase):
    """6 — les routes d'administration restent fermées."""

    def setUp(self):
        self.source = make_source()

    def test_anonymous_and_plain_users_cannot_reach_the_import_screens(self):
        for url in ("/admin/sourcing/listingsource/", "/admin/sourcing/listingimport/"):
            with self.subTest(url=url, who="anonyme"):
                response = self.client.get(url)
                self.assertEqual(response.status_code, status.HTTP_302_FOUND)
                self.assertIn("/admin/login/", response["Location"])

        self.client.force_login(User.objects.create_user(phone="+22670090002", password="pw"))
        for url in ("/admin/sourcing/listingsource/", "/admin/sourcing/listingimport/"):
            with self.subTest(url=url, who="utilisateur simple"):
                self.assertEqual(self.client.get(url).status_code, status.HTTP_302_FOUND)

    def test_a_staff_member_reaches_them(self):
        staff = User.objects.create_user(phone="+22670090003", password="pw")
        staff.is_staff = True
        staff.is_superuser = True
        staff.save()
        self.client.force_login(staff)

        self.assertEqual(self.client.get("/admin/sourcing/listingsource/").status_code, 200)
