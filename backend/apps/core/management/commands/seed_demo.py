"""Demo data seed: lets anyone spin up nogoya and see a working marketplace.

Idempotent: safe to re-run (uses get_or_create everywhere).
"""
import io
import random
import uuid
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify
from PIL import Image as PILImage

from apps.analytics.models import ContactEvent, ProductView
from apps.catalog.models import (
    Category,
    CategoryAttribute,
    Favorite,
    Product,
    ProductAttributeValue,
    ProductImage,
)
from apps.notifications.models import Notification
from apps.notifications.services import notify
from apps.suppliers.models import SupplierProfile

User = get_user_model()

# Per-category attributes, declared as data (see CategoryAttribute).
CATEGORY_ATTRIBUTES = {
    "Véhicules": [
        ("Kilométrage", "number", {"unit": "km", "filterable": True}),
    ],
    "Voitures": [
        ("Marque", "select", {"options": ["Toyota", "Peugeot", "Kia", "Hyundai", "Mercedes"],
                              "required": True, "filterable": True}),
        ("Année", "number", {"filterable": True}),
        ("Carburant", "select", {"options": ["Essence", "Diesel", "Hybride"], "filterable": True}),
        ("Boîte", "select", {"options": ["Manuelle", "Automatique"], "filterable": True}),
        ("Climatisation", "boolean", {"filterable": True}),
    ],
    "Motos": [
        ("Cylindrée", "number", {"unit": "cc", "filterable": True}),
        ("Marque", "text", {}),
    ],
    "Appartements": [
        ("Chambres", "number", {"required": True, "filterable": True}),
        ("Salles de bain", "number", {"filterable": True}),
        ("Surface", "number", {"unit": "m²", "filterable": True}),
        ("Meublé", "boolean", {"filterable": True}),
    ],
    "Ordinateurs": [
        ("Processeur", "text", {}),
        ("Mémoire vive", "number", {"unit": "Go", "filterable": True}),
        ("Stockage", "number", {"unit": "Go", "filterable": True}),
    ],
    "Sonorisation & vidéo": [
        ("Puissance", "number", {"unit": "W", "filterable": True}),
    ],
    "Tentes": [
        ("Capacité", "number", {"unit": "personnes", "filterable": True}),
    ],
}

# Attribute values for a few seeded products, keyed by product title.
PRODUCT_ATTRIBUTES = {
    "Berline climatisée avec chauffeur": {
        "marque": "Toyota", "annee": 2019, "carburant": "Diesel",
        "boite": "Automatique", "climatisation": True, "kilometrage": 85000,
    },
    "Moto 125cc en bon état": {"cylindree": 125, "marque": "Yamaha", "kilometrage": 12000},
    "Appartement meublé 2 chambres": {
        "chambres": 2, "salles-de-bain": 1, "surface": 75, "meuble": True,
    },
    "Ordinateur portable i5 8Go": {
        "processeur": "Intel Core i5-8250U", "memoire-vive": 8, "stockage": 256,
    },
    "Sono complète 2000W": {"puissance": 2000},
    "Tente de réception 10x5m": {"capacite": 100},
}

CATEGORY_TREE = {
    "Véhicules": ["Voitures", "Motos", "Utilitaires"],
    "Logements": ["Appartements", "Maisons", "Salles de fête"],
    "Équipements & Outils": ["Outillage", "Matériel agricole", "Matériel BTP"],
    "Électronique": ["Ordinateurs", "Sonorisation & vidéo"],
    "Événementiel": ["Chaises & tables", "Tentes", "Décoration"],
    "Mobilier": ["Salon", "Bureau"],
}

CITIES = ["Ouagadougou", "Bobo-Dioulasso", "Koudougou", "Ouahigouya"]

PRODUCT_SEEDS = [
    ("Tente de réception 10x5m", "Tentes", "rent", "day", 25000),
    ("Berline climatisée avec chauffeur", "Voitures", "rent", "day", 45000),
    ("Moto 125cc en bon état", "Motos", "sale", "none", 650000),
    ("Appartement meublé 2 chambres", "Appartements", "rent", "month", 180000),
    ("Bétonnière 150L", "Matériel BTP", "rent", "day", 15000),
    ("Sono complète 2000W", "Sonorisation & vidéo", "rent", "day", 35000),
    ("Lot de 100 chaises pliantes", "Chaises & tables", "rent", "day", 30000),
    ("Ordinateur portable i5 8Go", "Ordinateurs", "sale", "none", 275000),
    ("Salon 3+2+1 places", "Salon", "sale", "none", 195000),
    ("Motoculteur diesel", "Matériel agricole", "rent", "week", 40000),
]


def make_placeholder_image(label: str, color) -> ContentFile:
    img = PILImage.new("RGB", (640, 480), color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=80)
    buf.seek(0)
    return ContentFile(buf.read(), name=f"{label}.jpg")


PALETTE = [(5, 150, 105), (16, 118, 92), (217, 119, 6), (37, 99, 235), (219, 39, 119), (75, 85, 99)]


class Command(BaseCommand):
    help = "Seed demo categories, suppliers, products and images."

    @transaction.atomic
    def handle(self, *args, **options):
        categories = self._seed_categories()
        self._seed_category_attributes(categories)
        suppliers = self._seed_suppliers()
        visitor = self._seed_visitor()
        self._seed_products(categories, suppliers)
        self._seed_product_attributes()
        self._seed_engagement(visitor, suppliers)
        self.stdout.write(self.style.SUCCESS("Demo data ready."))
        self.stdout.write("Comptes de test (mot de passe: DemoPass123!) :")
        self.stdout.write("  Fournisseur : +22670010001 / +22670010002")
        self.stdout.write("  Visiteur    : +22670020001")
        self.stdout.write("  Admin       : +22670000000 / AdminPass123!")

    def _seed_categories(self):
        categories = {}
        for order, (parent_name, children) in enumerate(CATEGORY_TREE.items()):
            parent, _ = Category.objects.get_or_create(name=parent_name, defaults={"order": order})
            categories[parent_name] = parent
            for c_order, child_name in enumerate(children):
                child, _ = Category.objects.get_or_create(
                    name=child_name, defaults={"parent": parent, "order": c_order}
                )
                categories[child_name] = child
        return categories

    def _seed_suppliers(self):
        suppliers = []
        for i, (first, last, city) in enumerate([
            ("Issa", "Ouédraogo", "Ouagadougou"),
            ("Aminata", "Sawadogo", "Bobo-Dioulasso"),
        ], start=1):
            phone = f"+2267001000{i}"
            user, created = User.objects.get_or_create(
                phone=phone,
                defaults={"first_name": first, "last_name": last, "role": User.Role.SUPPLIER},
            )
            if created:
                user.set_password("DemoPass123!")
                user.save()
            profile, _ = SupplierProfile.objects.get_or_create(
                user=user, defaults={"city": city, "bio": f"Fournisseur professionnel basé à {city}.", "is_verified": True}
            )
            suppliers.append(profile)
        return suppliers

    def _seed_category_attributes(self, categories):
        for category_name, definitions in CATEGORY_ATTRIBUTES.items():
            category = categories.get(category_name)
            if category is None:
                continue
            for position, (name, kind, extra) in enumerate(definitions):
                CategoryAttribute.objects.get_or_create(
                    category=category, slug=slugify(name)[:140],
                    defaults={
                        "name": name,
                        "attribute_type": kind,
                        "position": position,
                        "required": extra.get("required", False),
                        "filterable": extra.get("filterable", False),
                        "unit": extra.get("unit", ""),
                        "options": extra.get("options", []),
                    },
                )

    def _seed_visitor(self):
        phone = "+22670020001"
        user, created = User.objects.get_or_create(
            phone=phone, defaults={"first_name": "Fatou", "last_name": "Kaboré", "role": User.Role.VISITOR}
        )
        if created:
            user.set_password("DemoPass123!")
            user.save()
        return user

    def _seed_product_attributes(self):
        for title, values in PRODUCT_ATTRIBUTES.items():
            product = Product.objects.filter(title=title).select_related("category").first()
            if product is None or product.category is None:
                continue
            definitions = {a.slug: a for a in product.category.effective_attributes()}
            for slug, value in values.items():
                definition = definitions.get(slug)
                if definition is None:
                    continue
                ProductAttributeValue.objects.get_or_create(
                    product=product, attribute=definition, defaults={"value": value}
                )

    def _seed_engagement(self, visitor, suppliers):
        """Favourites, views, contacts and notifications so the dashboards
        and the user home page are not empty on a fresh install."""
        products = list(Product.objects.filter(status=Product.Status.APPROVED)[:6])
        if not products:
            return

        for product in products[:3]:
            Favorite.objects.get_or_create(user=visitor, product=product)

        now = timezone.now()
        if not ProductView.objects.exists():
            for product in products:
                for day in range(14):
                    for _ in range(random.randint(0, 3)):
                        view = ProductView.objects.create(
                            product=product, visitor_id=uuid.uuid4().hex
                        )
                        # created_at is auto_now_add, so backdate it afterwards
                        # to give the dashboard charts a realistic spread.
                        ProductView.objects.filter(pk=view.pk).update(
                            created_at=now - timedelta(days=day, hours=random.randint(0, 20))
                        )
                if random.random() > 0.5:
                    contact = ContactEvent.objects.create(
                        product=product, user=visitor, channel="phone"
                    )
                    ContactEvent.objects.filter(pk=contact.pk).update(
                        created_at=now - timedelta(days=random.randint(0, 13))
                    )

        if not Notification.objects.filter(user=visitor).exists():
            notify(
                visitor,
                type=Notification.Type.NEW_PRODUCT,
                title="Nouvelles annonces disponibles",
                message="Des articles correspondant à vos centres d'intérêt viennent d'être publiés.",
                url="/produits",
            )
        for supplier in suppliers:
            if not Notification.objects.filter(user=supplier.user).exists():
                notify(
                    supplier.user,
                    type=Notification.Type.SYSTEM,
                    title="Bienvenue sur nogoya",
                    message="Complétez votre profil fournisseur pour inspirer confiance aux visiteurs.",
                    url="/compte/fournisseur/parametres",
                )

    def _seed_products(self, categories, suppliers):
        for idx, (title, cat_name, listing_type, period, price) in enumerate(PRODUCT_SEEDS):
            existing = Product.objects.filter(title=title).first()
            if existing is not None:
                # Demo listings are meant to be browsable. Editing one (by
                # hand or from the E2E suite) sends it back to moderation, so
                # re-running the seed restores the demo state it promises.
                if existing.status != Product.Status.APPROVED or not existing.is_active:
                    Product.objects.filter(pk=existing.pk).update(
                        status=Product.Status.APPROVED, is_active=True
                    )
                    self.stdout.write(f"  ~ {title} remis en ligne")
                continue
            product = Product.objects.create(
                supplier=suppliers[idx % len(suppliers)],
                category=categories[cat_name],
                title=title,
                description=f"{title}. Disponible immédiatement, contactez le fournisseur pour plus de détails.",
                price=price,
                listing_type=listing_type,
                rental_period=period,
                city=random.choice(CITIES),
                status=Product.Status.APPROVED,
                views_count=random.randint(0, 200),
            )
            color = PALETTE[idx % len(PALETTE)]
            image = ProductImage.objects.create(
                product=product,
                image=make_placeholder_image(f"product-{idx}", color),
                is_cover=True,
                width=640,
                height=480,
            )
            self.stdout.write(f"  + {product.title} (image #{image.pk})")
