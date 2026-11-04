"""Le parcours d'une demande de location, et le verrou sur les coordonnées.

Le cœur du schéma intermédié tient en une phrase : **un client ne voit le
numéro du fournisseur que si l'équipe le lui a transmis, après avoir
vérifié la disponibilité.** Ces tests portent surtout sur les refus, parce
que c'est là que la promesse se tient ou se perd.
"""
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.catalog.models import Category, Product
from apps.messaging.models import Conversation

from .models import RentalRequest

User = get_user_model()


class RentalRequestFlowTests(APITestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Logements")
        self.supplier = User.objects.create_user(
            phone="+22670040001", password="pw", role=User.Role.SUPPLIER
        )
        self.supplier.supplier_profile.whatsapp_number = "+22670040001"
        self.supplier.supplier_profile.save()
        self.client_user = User.objects.create_user(phone="+22670040002", password="pw")
        self.other_client = User.objects.create_user(phone="+22670040003", password="pw")
        self.staff = User.objects.create_user(phone="+22670040009", password="pw")
        self.staff.is_staff = True
        self.staff.save(update_fields=["is_staff"])

        self.product = Product.objects.create(
            supplier=self.supplier.supplier_profile, category=self.category,
            title="Appartement 2 chambres", price=150000, city="Ouagadougou",
            status=Product.Status.APPROVED, is_active=True,
        )
        self.start = date.today() + timedelta(days=7)
        self.end = self.start + timedelta(days=5)
        self.list_url = reverse("api:rental-request-list")
        self.contact_url = reverse("api:product-contact", args=[self.product.slug])

    def _submit(self, user=None, **overrides):
        self.client.force_authenticate(user or self.client_user)
        payload = {
            "product": self.product.pk,
            "start_date": self.start.isoformat(),
            "end_date": self.end.isoformat(),
            "message": "Bonjour, est-ce libre ?",
            **overrides,
        }
        return self.client.post(self.list_url, payload, format="json")

    # --- soumission ----------------------------------------------------

    def test_a_client_submits_a_request_with_dates(self):
        resp = self._submit()
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)

        demande = RentalRequest.objects.get()
        self.assertEqual(demande.client, self.client_user)
        self.assertEqual(demande.status, RentalRequest.Status.SUBMITTED)
        self.assertEqual(demande.nights, 6)  # bornes comprises
        # Rien n'est transmis tant que l'équipe n'a rien décidé.
        self.assertIsNone(demande.supplier_checked_at)
        self.assertIsNone(demande.contact_released_at)

    def test_the_request_opens_the_thread_with_nogoya_on_that_listing(self):
        """Le client n'a pas à chercher où suivre son dossier."""
        self._submit()
        demande = RentalRequest.objects.get()
        self.assertIsNotNone(demande.thread_id)
        self.assertEqual(demande.thread.initial_product, self.product)
        self.assertEqual(demande.thread.audience, Conversation.Audience.CLIENT)

    def test_an_inverted_date_range_is_refused(self):
        resp = self._submit(
            start_date=self.end.isoformat(), end_date=self.start.isoformat()
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("end_date", resp.data)

    def test_a_supplier_cannot_request_their_own_listing(self):
        resp = self._submit(self.supplier)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    # --- le visiteur sans compte ---------------------------------------

    def test_a_visitor_without_an_account_may_ask(self):
        """Exiger une inscription avant la premiere question fait fuir.

        Le schema ne l'impose pas : c'est NOGOYA qui rappelle, et un numero
        suffit pour cela.
        """
        self.client.force_authenticate(None)
        resp = self.client.post(
            self.list_url,
            {
                "product": self.product.pk,
                "start_date": self.start.isoformat(),
                "end_date": self.end.isoformat(),
                "guest_name": "Awa Traore",
                "guest_phone": "70 11 22 33",
                "message": "Disponible ?",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)

        demande = RentalRequest.objects.get()
        self.assertIsNone(demande.client_id)
        # Le numero est normalise a l'enregistrement.
        self.assertEqual(demande.guest_phone, "70112233")
        self.assertEqual(demande.requester_label, "Awa Traore")
        # Sans compte, pas de fil : nous rappellerons.
        self.assertIsNone(demande.thread_id)

    def test_a_visitor_without_a_phone_is_refused(self):
        """Sans compte ni numero, la demande serait une impasse."""
        self.client.force_authenticate(None)
        resp = self.client.post(
            self.list_url,
            {
                "product": self.product.pk,
                "start_date": self.start.isoformat(),
                "end_date": self.end.isoformat(),
                "guest_name": "Awa",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("guest_phone", resp.data)
        self.assertFalse(RentalRequest.objects.exists())

    def test_a_signed_in_client_cannot_pass_someone_elses_number(self):
        resp = self._submit(guest_phone="70999999", guest_name="Quelqu un d autre")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        demande = RentalRequest.objects.get()
        self.assertEqual(demande.guest_phone, "")
        self.assertEqual(demande.client, self.client_user)

    def test_a_guest_request_never_lists_itself_to_others(self):
        self.client.force_authenticate(None)
        self.client.post(
            self.list_url,
            {
                "product": self.product.pk, "start_date": self.start.isoformat(),
                "end_date": self.end.isoformat(), "guest_phone": "70112233",
            },
            format="json",
        )
        self.client.force_authenticate(self.client_user)
        self.assertEqual(self.client.get(self.list_url).data["count"], 0)

    # --- duree indeterminee ---------------------------------------------

    def test_a_house_may_be_asked_without_an_end_date(self):
        """Demander une date de fin pour un logement n'a pas de sens."""
        resp = self._submit(end_date=None, open_ended=True)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)

        demande = RentalRequest.objects.get()
        self.assertIsNone(demande.end_date)
        self.assertTrue(demande.open_ended)
        self.assertIsNone(demande.nights)

    def test_an_end_date_is_required_unless_the_duration_is_open(self):
        resp = self._submit(end_date=None)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("end_date", resp.data)

    def test_checking_an_open_duration_drops_any_end_date_given(self):
        """On efface la date plutot que d'en garder une qui ne veut rien dire."""
        self._submit(open_ended=True)
        self.assertIsNone(RentalRequest.objects.get().end_date)

    # --- le recapitulatif dans le fil ------------------------------------

    def test_the_thread_opens_with_a_summary_not_an_empty_chat(self):
        """L'equipe ouvrait une conversation vide, sans savoir de quoi il s'agit."""
        from apps.messaging.models import Message

        self._submit()
        demande = RentalRequest.objects.get()
        recap = Message.objects.get(conversation=demande.thread)

        self.assertEqual(recap.message_type, Message.Type.SYSTEM)
        # Le bien est porte par la carte jointe, pas recopie dans le texte :
        # le lire sans pouvoir l'ouvrir obligeait a le chercher a la main.
        self.assertEqual(recap.shared_product, self.product)
        self.assertIn("Bonjour, est-ce libre ?", recap.body)
        self.assertIn(f"{self.start:%d/%m/%Y}", recap.body)
        # Lu d'emblee : c'est un recapitulatif, pas une question en attente.
        self.assertIsNotNone(recap.read_at)

    def test_two_requests_from_the_same_client_share_one_thread(self):
        """Une conversation par personne, pas par demande."""
        from apps.messaging.models import Conversation, Message

        autre = Product.objects.create(
            supplier=self.supplier.supplier_profile, category=self.category,
            title="Studio meuble", price=90000, city="Ouagadougou",
            status=Product.Status.APPROVED, is_active=True,
        )
        self._submit()
        self._submit(product=autre.pk)

        fils = Conversation.objects.filter(participant_low=self.client_user) |             Conversation.objects.filter(participant_high=self.client_user)
        self.assertEqual(fils.distinct().count(), 1)
        # Mais les deux recapitulatifs sont la, chacun avec son annonce.
        recaps = Message.objects.filter(message_type=Message.Type.SYSTEM)
        self.assertEqual(recaps.count(), 2)
        self.assertEqual(
            {m.shared_product_id for m in recaps}, {self.product.pk, autre.pk}
        )

    def test_the_summary_carries_the_listing_so_it_is_clickable(self):
        """Lire le nom du bien sans pouvoir l'ouvrir obligeait a le chercher."""
        from apps.messaging.models import Message

        self._submit()
        recap = Message.objects.get(message_type=Message.Type.SYSTEM)
        self.assertEqual(recap.shared_product, self.product)

    def test_the_summary_says_when_the_duration_is_open(self):
        from apps.messaging.models import Message

        self._submit(end_date=None, open_ended=True)
        recap = Message.objects.get(conversation=RentalRequest.objects.get().thread)
        self.assertIn("duree indeterminee", recap.body.replace("é", "e"))

    # --- le verrou sur les coordonnées ----------------------------------

    def test_the_contact_is_refused_until_the_team_releases_it(self):
        self._submit()
        self.client.force_authenticate(self.client_user)

        resp = self.client.post(self.contact_url)
        self.assertEqual(resp.status_code, status.HTTP_409_CONFLICT)
        self.assertTrue(resp.data["needs_rental_request"])
        self.assertNotIn(self.supplier.phone, str(resp.data))

    def test_releasing_requires_a_verified_availability(self):
        self._submit()
        demande = RentalRequest.objects.get()
        self.client.force_authenticate(self.staff)

        resp = self.client.post(reverse("api:rental-request-release-contact", args=[demande.pk]))
        self.assertEqual(resp.status_code, status.HTTP_409_CONFLICT)
        demande.refresh_from_db()
        self.assertIsNone(demande.contact_released_at)

    def test_the_full_path_availability_then_release_then_contact(self):
        self._submit()
        demande = RentalRequest.objects.get()
        self.client.force_authenticate(self.staff)

        self.client.post(reverse("api:rental-request-available", args=[demande.pk]))
        demande.refresh_from_db()
        self.assertEqual(demande.status, RentalRequest.Status.AVAILABLE)
        # La preuve que quelqu'un a réellement appelé le fournisseur.
        self.assertIsNotNone(demande.supplier_checked_at)

        released = self.client.post(
            reverse("api:rental-request-release-contact", args=[demande.pk])
        )
        self.assertEqual(released.status_code, status.HTTP_200_OK, released.data)
        demande.refresh_from_db()
        self.assertEqual(demande.status, RentalRequest.Status.CONNECTED)
        self.assertEqual(demande.released_by, self.staff)

        self.client.force_authenticate(self.client_user)
        contact = self.client.post(self.contact_url)
        self.assertEqual(contact.status_code, status.HTTP_200_OK, contact.data)
        self.assertEqual(contact.data["phone"], self.supplier.phone)

    def test_an_unavailable_listing_is_never_connected(self):
        """La seule faute que ce schéma existe pour éviter."""
        self._submit()
        demande = RentalRequest.objects.get()
        self.client.force_authenticate(self.staff)
        self.client.post(reverse("api:rental-request-unavailable", args=[demande.pk]))

        resp = self.client.post(reverse("api:rental-request-release-contact", args=[demande.pk]))
        self.assertEqual(resp.status_code, status.HTTP_409_CONFLICT)

        self.client.force_authenticate(self.client_user)
        self.assertEqual(self.client.post(self.contact_url).status_code, status.HTTP_409_CONFLICT)

    def test_a_release_benefits_only_the_client_it_was_granted_to(self):
        self._submit()
        demande = RentalRequest.objects.get()
        self.client.force_authenticate(self.staff)
        self.client.post(reverse("api:rental-request-available", args=[demande.pk]))
        self.client.post(reverse("api:rental-request-release-contact", args=[demande.pk]))

        self.client.force_authenticate(self.other_client)
        resp = self.client.post(self.contact_url)
        self.assertEqual(resp.status_code, status.HTTP_409_CONFLICT)

    def test_a_supplier_always_sees_their_own_contact(self):
        self.client.force_authenticate(self.supplier)
        resp = self.client.post(self.contact_url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)

    # --- qui peut décider quoi ------------------------------------------

    def test_a_client_cannot_declare_a_listing_available(self):
        """Le contrôle est côté serveur : masquer un bouton ne protège rien."""
        self._submit()
        demande = RentalRequest.objects.get()
        self.client.force_authenticate(self.client_user)

        for route in ("available", "unavailable", "checking", "release-contact"):
            with self.subTest(route=route):
                resp = self.client.post(
                    reverse(f"api:rental-request-{route}", args=[demande.pk])
                )
                self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

        demande.refresh_from_db()
        self.assertEqual(demande.status, RentalRequest.Status.SUBMITTED)

    def test_a_client_may_cancel_their_own_request(self):
        self._submit()
        demande = RentalRequest.objects.get()
        self.client.force_authenticate(self.client_user)

        resp = self.client.post(reverse("api:rental-request-cancel", args=[demande.pk]))
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        demande.refresh_from_db()
        self.assertEqual(demande.status, RentalRequest.Status.CANCELLED)

    def test_the_team_is_told_how_many_requests_have_no_account(self):
        """Personne ne relancera a la place d'un visiteur anonyme.

        Sans fil, ces demandes n'apparaissent dans aucune conversation :
        le compteur est ce qui les rend visibles la ou l'equipe regarde.
        """
        self._submit()
        self.client.force_authenticate(None)
        self.client.post(
            self.list_url,
            {
                "product": self.product.pk, "start_date": self.start.isoformat(),
                "end_date": self.end.isoformat(), "guest_phone": "70112233",
            },
            format="json",
        )

        self.client.force_authenticate(self.staff)
        data = self.client.get(reverse("api:rental-request-pending-summary")).data
        self.assertEqual(data["pending"], 2)
        self.assertEqual(data["without_account"], 1)

    def test_a_treated_request_leaves_the_counter(self):
        self._submit()
        demande = RentalRequest.objects.get()
        self.client.force_authenticate(self.staff)
        self.client.post(reverse("api:rental-request-available", args=[demande.pk]))

        data = self.client.get(reverse("api:rental-request-pending-summary")).data
        self.assertEqual(data["pending"], 0)

    def test_the_counter_is_closed_to_everyone_else(self):
        self._submit()
        for who in (None, self.client_user, self.supplier):
            with self.subTest(who=getattr(who, "phone", "anonyme")):
                self.client.force_authenticate(who)
                resp = self.client.get(reverse("api:rental-request-pending-summary"))
                self.assertIn(
                    resp.status_code,
                    (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
                )

    # --- ce que chacun lit ----------------------------------------------

    def test_a_client_sees_only_their_own_requests(self):
        self._submit()
        self._submit(self.other_client)

        self.client.force_authenticate(self.client_user)
        mine = self.client.get(self.list_url)
        self.assertEqual(mine.data["count"], 1)

        self.client.force_authenticate(self.staff)
        self.assertEqual(self.client.get(self.list_url).data["count"], 2)

    def test_the_internal_note_never_reaches_the_client(self):
        self._submit()
        demande = RentalRequest.objects.get()
        self.client.force_authenticate(self.staff)
        self.client.post(
            reverse("api:rental-request-checking", args=[demande.pk]),
            {"staff_note": "Fournisseur injoignable, rappeler demain"},
            format="json",
        )

        self.client.force_authenticate(self.client_user)
        body = str(self.client.get(self.list_url).data)
        self.assertNotIn("injoignable", body)
        self.assertNotIn(self.staff.phone, body)

    def test_the_team_can_filter_the_queue_by_status(self):
        self._submit()
        demande = RentalRequest.objects.get()
        self.client.force_authenticate(self.staff)
        self.client.post(reverse("api:rental-request-available", args=[demande.pk]))

        waiting = self.client.get(self.list_url, {"status": "submitted"})
        self.assertEqual(waiting.data["count"], 0)
        ready = self.client.get(self.list_url, {"status": "available"})
        self.assertEqual(ready.data["count"], 1)
