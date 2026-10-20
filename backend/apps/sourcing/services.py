"""Le trajet d'une annonce, de la source au brouillon à valider.

    adaptateur -> normalisation -> qualité -> déduplication -> brouillon

Rien n'est publié automatiquement. Une annonce importée naît en
`Status.DRAFT` et attend qu'un humain la regarde ; c'est la seule garantie
sérieuse contre une source qui change de format, un prix mal lu ou un bien
qui n'existe plus.

Le compte « propriétaire » d'une annonce référencée est un compte de
service, pas une personne. Il porte l'annonce techniquement parce que
`Product.supplier` est obligatoire ; `provenance` dit la vérité, et les
sérialiseurs n'exposent jamais ce compte comme un vendeur.
"""
import logging
from dataclasses import dataclass, field

from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.catalog.models import Product
from apps.suppliers.models import SupplierProfile

from .adapters.base import AdapterError, get_adapter
from .fingerprints import find_probable_duplicate, fingerprint
from .models import ListingImport, ListingSource
from .normalization import match_category, parse_price
from .quality import check

logger = logging.getLogger("nogoya.sourcing")

SERVICE_ACCOUNT_PHONE = "+22600000000"
SERVICE_ACCOUNT_NAME = "NOGOYA — annonces référencées"


@dataclass
class ImportReport:
    """Ce que l'exécution a fait, dans des termes vérifiables."""

    source: str
    seen: int = 0
    created: int = 0
    updated: int = 0
    duplicates: int = 0
    invalid: int = 0
    expired: int = 0
    errors: list = field(default_factory=list)
    started_at: str = ""
    finished_at: str = ""

    @property
    def status(self):
        if self.errors and not (self.created or self.updated):
            return ListingSource.RunStatus.FAILED
        if self.errors:
            return ListingSource.RunStatus.PARTIAL
        return ListingSource.RunStatus.OK

    def as_dict(self):
        return {
            "source": self.source,
            "seen": self.seen,
            "created": self.created,
            "updated": self.updated,
            "duplicates": self.duplicates,
            "invalid": self.invalid,
            "expired": self.expired,
            "errors": self.errors[:50],
            "started_at": self.started_at,
            "finished_at": self.finished_at,
        }

    def summary(self):
        return (
            f"{self.source} : {self.seen} vue(s), {self.created} créée(s), "
            f"{self.updated} mise(s) à jour, {self.duplicates} doublon(s), "
            f"{self.invalid} écartée(s), {self.expired} expirée(s), "
            f"{len(self.errors)} erreur(s)"
        )


def import_service_supplier():
    """Le compte au nom duquel les annonces référencées sont enregistrées.

    Ce n'est **pas** un faux propriétaire : il est nommé pour ce qu'il est,
    n'a pas de numéro joignable publié, et aucune vue n'expose son profil
    pour une annonce dont la provenance n'est pas `nogoya_owner`.
    """
    user, created = User.objects.get_or_create(
        phone=SERVICE_ACCOUNT_PHONE,
        defaults={
            # `User` n'a pas de `full_name` : il hérite de first_name/last_name.
            "first_name": "NOGOYA",
            "last_name": "— annonces référencées",
            "role": User.Role.SUPPLIER,
            "is_active": False,
        },
    )
    if created:
        # Compte technique : aucun mot de passe utilisable, aucune connexion.
        user.set_unusable_password()
        user.is_active = False
        user.save(update_fields=["password", "is_active"])
    profile, _ = SupplierProfile.objects.get_or_create(
        user=user, defaults={"city": "", "bio": SERVICE_ACCOUNT_NAME}
    )
    return profile


def normalize(raw, source):
    """`RawListing` -> dictionnaire prêt pour la création d'un produit."""
    price, currency, period = parse_price(raw.price_text)
    if raw.currency:
        currency = raw.currency.strip().upper() or currency
    if raw.price_period in dict(Product.RentalPeriod.choices):
        period = raw.price_period

    category = match_category(raw.category_hint, raw.title or "", raw.description or "")

    listing_type = (raw.listing_type or "").strip().lower()
    if listing_type not in dict(Product.ListingType.choices):
        # Une source de locations ne dit pas toujours qu'elle loue ; la
        # valeur par défaut est déclarée dans la configuration de la source,
        # pas devinée ici.
        listing_type = (source.config or {}).get("default_listing_type", Product.ListingType.RENT)

    return {
        "external_id": raw.external_id or "",
        "original_url": (raw.original_url or "").strip(),
        "title": (raw.title or "").strip()[:200],
        "description": (raw.description or "").strip(),
        "price": price,
        "currency": currency or "XOF",
        "rental_period": period or Product.RentalPeriod.MONTH,
        "listing_type": listing_type,
        "city": (raw.city or "").strip()[:120],
        "location": (raw.area or "").strip()[:255],
        "region": (raw.region or "").strip()[:120],
        "country": (raw.country or "Burkina Faso").strip()[:120],
        "category_id": category.pk if category else None,
        # Les photos ne sont retenues que si la source l'autorise : une
        # photo appartient à qui l'a prise, pas à qui l'a publiée.
        "image_urls": list(raw.image_urls) if source.allows_image_reuse else [],
        "contact_public": (raw.contact_public or "") if source.allows_contact_details else "",
    }


def run_import(source, *, limit=None, dry_run=False):
    """Exécute une source et renvoie son rapport.

    Ne lève pas : une source cassée produit un rapport en échec, pas une
    exception qui interromprait les suivantes.
    """
    report = ImportReport(source=source.name, started_at=timezone.now().isoformat())

    if not source.is_active:
        report.errors.append("Source inactive : rien n'a été interrogé.")
        report.finished_at = timezone.now().isoformat()
        return report

    cap = min(limit or source.max_items_per_run, source.max_items_per_run)

    try:
        listings = list(_take(get_adapter(source).fetch(), cap))
    except AdapterError as exc:
        report.errors.append(str(exc))
        report.finished_at = timezone.now().isoformat()
        _record_run(source, report, dry_run)
        return report
    except Exception as exc:  # une source tierce peut échouer de mille façons
        logger.exception("Source %s : échec inattendu", source.slug)
        report.errors.append(f"Échec inattendu : {exc}")
        report.finished_at = timezone.now().isoformat()
        _record_run(source, report, dry_run)
        return report

    seen_fingerprints = []
    for raw in listings:
        report.seen += 1
        try:
            outcome, key = _ingest(raw, source, report, dry_run)
            if key:
                seen_fingerprints.append(key)
            logger.debug("%s -> %s", source.slug, outcome)
        except Exception as exc:
            logger.exception("Source %s : annonce ignorée", source.slug)
            report.errors.append(f"{raw.title or raw.external_id or '?'} : {exc}")

    # Y compris quand la source ne renvoie plus rien : c'est le cas où tout
    # doit expirer. Une source réellement en panne lève une `AdapterError`
    # (HTTP en erreur, flux vide, fichier absent), remplit `report.errors`,
    # et n'arrive donc jamais ici — la distinction tient à cela.
    if not dry_run:
        _flag_disappeared(source, seen_fingerprints, report)

    report.finished_at = timezone.now().isoformat()
    _record_run(source, report, dry_run)
    return report


def _take(iterable, cap):
    for index, item in enumerate(iterable):
        if index >= cap:
            return
        yield item


@transaction.atomic
def _ingest(raw, source, report, dry_run):
    normalized = normalize(raw, source)
    key = fingerprint(
        external_id=normalized["external_id"] or None,
        original_url=normalized["original_url"] or None,
        title=normalized["title"],
        city=normalized["city"],
        price=normalized["price"],
        category_id=normalized["category_id"],
    )
    now = timezone.now()

    record = ListingImport.objects.filter(source=source, fingerprint=key).first()
    problems = check(normalized, source=source)

    if dry_run:
        if problems:
            report.invalid += 1
        elif record and record.product_id:
            report.updated += 1
        else:
            report.created += 1
        return "simulation", key

    payload = {
        "external_id": normalized["external_id"][:255],
        "original_url": normalized["original_url"][:500],
        "normalized": _jsonable(normalized),
        "raw_payload": _jsonable(raw.raw),
        "last_checked_at": now,
    }

    if record is None:
        record = ListingImport(
            source=source, fingerprint=key, collected_at=raw.collected_at or now, **payload
        )
    else:
        for attribute, value in payload.items():
            setattr(record, attribute, value)

    if problems:
        record.status = ListingImport.Status.INVALID
        record.error_message = " ".join(problems)
        record.save()
        report.invalid += 1
        return "écartée", key

    record.error_message = ""

    # L'annonce existe déjà : on rafraîchit plutôt que de recréer.
    if record.product_id:
        _refresh_product(record.product, normalized, now)
        record.status = ListingImport.Status.IMPORTED
        record.save()
        report.updated += 1
        return "mise à jour", key

    twin = find_probable_duplicate(
        title=normalized["title"],
        city=normalized["city"],
        price=normalized["price"],
        category_id=normalized["category_id"],
    )
    if twin is not None:
        # On ne fusionne pas et on ne crée rien : on garde la trace du
        # rapprochement pour qu'un humain tranche.
        record.status = ListingImport.Status.DUPLICATE
        record.error_message = f"Rapprochement avec l'annonce existante #{twin.pk} « {twin.title} »."
        record.save()
        report.duplicates += 1
        return "doublon", key

    record.product = _create_draft(normalized, source, now)
    record.status = ListingImport.Status.IMPORTED
    record.save()
    report.created += 1
    return "créée", key


def _create_draft(normalized, source, now):
    provenance = (
        Product.Provenance.AUTHORIZED_PARTNER
        if source.kind == ListingSource.Kind.FILE
        else Product.Provenance.EXTERNAL_REFERENCE
    )
    return Product.objects.create(
        supplier=import_service_supplier(),
        category_id=normalized["category_id"],
        title=normalized["title"],
        description=normalized["description"],
        price=normalized["price"],
        currency=normalized["currency"],
        listing_type=normalized["listing_type"],
        rental_period=normalized["rental_period"],
        city=normalized["city"],
        location=normalized["location"],
        region=normalized["region"],
        country=normalized["country"],
        # Jamais publiée par un programme : un humain valide.
        status=Product.Status.DRAFT,
        is_active=False,
        provenance=provenance,
        source=source,
        source_url=normalized["original_url"],
        last_checked_at=now,
    )


def _refresh_product(product, normalized, now):
    """Remet à jour ce qui peut changer chez la source, sans republier.

    Le statut n'est pas touché : une annonce rejetée par un modérateur ne
    doit pas se relever toute seule à la prochaine exécution.
    """
    product.price = normalized["price"]
    product.currency = normalized["currency"]
    product.city = normalized["city"]
    product.source_url = normalized["original_url"]
    product.last_checked_at = now
    if product.status in (Product.Status.EXPIRED, Product.Status.UNAVAILABLE):
        # Réapparue chez la source : elle redevient un brouillon à revoir.
        product.status = Product.Status.DRAFT
    product.save(
        update_fields=["price", "currency", "city", "source_url", "last_checked_at", "status", "updated_at"]
    )


def _flag_disappeared(source, seen_fingerprints, report):
    """Marque expirées les annonces que la source ne présente plus.

    Uniquement quand l'exécution s'est bien passée : une source qui renvoie
    une page vide à cause d'une panne ne doit pas vider le catalogue.
    """
    if report.errors:
        return
    stale = ListingImport.objects.filter(
        source=source, status=ListingImport.Status.IMPORTED
    ).exclude(fingerprint__in=seen_fingerprints)

    for record in stale.select_related("product"):
        record.status = ListingImport.Status.EXPIRED
        record.last_checked_at = timezone.now()
        record.save(update_fields=["status", "last_checked_at", "updated_at"])
        report.expired += 1
        if record.product_id:
            Product.objects.filter(pk=record.product_id).update(
                status=Product.Status.EXPIRED, is_active=False, last_checked_at=timezone.now()
            )


def _record_run(source, report, dry_run):
    if dry_run:
        return
    ListingSource.objects.filter(pk=source.pk).update(
        last_run_at=timezone.now(),
        last_run_status=report.status,
        last_run_report=report.as_dict(),
    )


def _jsonable(value):
    """Rend une structure sérialisable en JSON sans perdre les décimaux."""
    from decimal import Decimal

    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, Decimal):
        return str(value)
    return value
