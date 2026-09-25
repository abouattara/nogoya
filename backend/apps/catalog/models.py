import uuid

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel
from apps.suppliers.models import SupplierProfile


def product_image_upload_to(instance, filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "jpg"
    return f"products/{uuid.uuid4().hex}.{ext}"


class Category(models.Model):
    name = models.CharField(_("nom"), max_length=120, unique=True)
    slug = models.SlugField(_("slug"), max_length=140, unique=True, blank=True)
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="children"
    )
    icon = models.CharField(_("icône"), max_length=60, blank=True)
    order = models.PositiveIntegerField(_("ordre"), default=0)

    class Meta:
        verbose_name = _("catégorie")
        verbose_name_plural = _("catégories")
        ordering = ["order", "name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:140]
        super().save(*args, **kwargs)

    def effective_attributes(self):
        """Own attributes + those inherited from the parent category.

        A sub-category ("Voitures") inherits the generic attributes of its
        parent ("Véhicules") so common fields are declared only once.
        """
        own = list(self.attributes.all())
        if self.parent_id:
            own_slugs = {a.slug for a in own}
            own += [a for a in self.parent.attributes.all() if a.slug not in own_slugs]
        return sorted(own, key=lambda a: (a.position, a.name))

    def __str__(self):
        return self.name


class CategoryAttribute(models.Model):
    """A per-category field (marque, année, surface...) declared in data.

    Keeps `Product` free of category-specific columns: adding "nombre de
    chambres" to Logements is an admin action, not a migration.
    """

    class AttributeType(models.TextChoices):
        TEXT = "text", _("Texte")
        NUMBER = "number", _("Nombre")
        BOOLEAN = "boolean", _("Oui / Non")
        SELECT = "select", _("Liste déroulante")
        MULTI_SELECT = "multi_select", _("Choix multiples")
        DATE = "date", _("Date")

    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="attributes")
    name = models.CharField(_("nom"), max_length=120)
    slug = models.SlugField(_("slug"), max_length=140, blank=True)
    attribute_type = models.CharField(
        _("type"), max_length=16, choices=AttributeType.choices, default=AttributeType.TEXT
    )
    required = models.BooleanField(_("obligatoire"), default=False)
    filterable = models.BooleanField(_("filtrable"), default=False)
    searchable = models.BooleanField(_("recherchable"), default=False)
    unit = models.CharField(_("unité"), max_length=20, blank=True, help_text=_("Ex : km, m², ch"))
    options = models.JSONField(
        _("options"), default=list, blank=True,
        help_text=_("Valeurs possibles pour les types liste : [\"Essence\", \"Diesel\"]"),
    )
    position = models.PositiveIntegerField(_("ordre"), default=0)

    class Meta:
        verbose_name = _("attribut de catégorie")
        verbose_name_plural = _("attributs de catégorie")
        ordering = ["position", "name"]
        constraints = [
            models.UniqueConstraint(fields=["category", "slug"], name="unique_attribute_slug_per_category"),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:140]
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.category.name} · {self.name}"


class Product(TimeStampedModel):
    class ListingType(models.TextChoices):
        RENT = "rent", _("Location")
        SALE = "sale", _("Vente")

    class RentalPeriod(models.TextChoices):
        HOUR = "hour", _("Heure")
        DAY = "day", _("Jour")
        WEEK = "week", _("Semaine")
        MONTH = "month", _("Mois")
        NONE = "none", _("—")

    class Status(models.TextChoices):
        PENDING = "pending", _("En attente")
        APPROVED = "approved", _("Approuvé")
        REJECTED = "rejected", _("Rejeté")

    class LocationPrecision(models.TextChoices):
        EXACT = "exact", _("Position exacte")
        APPROXIMATE = "approximate", _("Position approximative")

    supplier = models.ForeignKey(
        SupplierProfile, on_delete=models.CASCADE, related_name="products"
    )
    category = models.ForeignKey(
        Category, null=True, on_delete=models.SET_NULL, related_name="products"
    )
    title = models.CharField(_("titre"), max_length=200)
    slug = models.SlugField(_("slug"), max_length=220, unique=True, blank=True)
    description = models.TextField(_("description"), blank=True)
    price = models.DecimalField(
        _("prix"), max_digits=12, decimal_places=0, validators=[MinValueValidator(0)]
    )
    currency = models.CharField(_("devise"), max_length=8, default="XOF")
    listing_type = models.CharField(
        _("type"), max_length=8, choices=ListingType.choices, default=ListingType.RENT
    )
    rental_period = models.CharField(
        _("période"), max_length=8, choices=RentalPeriod.choices, default=RentalPeriod.DAY
    )
    city = models.CharField(_("ville"), max_length=120, db_index=True)
    location = models.CharField(_("localisation"), max_length=255, blank=True)
    region = models.CharField(_("région"), max_length=120, blank=True)
    country = models.CharField(_("pays"), max_length=120, blank=True, default="Burkina Faso")
    latitude = models.DecimalField(
        _("latitude"), max_digits=9, decimal_places=6, null=True, blank=True
    )
    longitude = models.DecimalField(
        _("longitude"), max_digits=9, decimal_places=6, null=True, blank=True
    )
    place_id = models.CharField(_("place id (Google Maps)"), max_length=255, blank=True)
    location_precision = models.CharField(
        _("précision de la localisation"), max_length=12,
        choices=LocationPrecision.choices, default=LocationPrecision.APPROXIMATE,
        help_text=_("Le fournisseur choisit s'il expose la position exacte ou seulement la ville."),
    )
    status = models.CharField(
        _("statut"), max_length=12, choices=Status.choices, default=Status.PENDING,
        db_index=True,
    )
    is_active = models.BooleanField(
        _("visible"), default=True,
        help_text=_("Le fournisseur peut dépublier une annonce approuvée sans repasser par la modération."),
    )
    views_count = models.PositiveIntegerField(_("vues"), default=0)
    shares_count = models.PositiveIntegerField(_("partages"), default=0)
    published_at = models.DateTimeField(_("publié le"), null=True, blank=True)

    class Meta:
        verbose_name = _("produit")
        verbose_name_plural = _("produits")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "is_active", "listing_type", "city"]),
            models.Index(fields=["category", "status", "is_active"]),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)[:200] or "produit"
            slug, n = base, 1
            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                n += 1
                slug = f"{base}-{n}"
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        """Where a moderator lands from the admin's "view on site" link.

        The listing page lives in the Next.js frontend, not here.
        """
        return f"{settings.FRONTEND_URL}/produits/{self.slug}"

    @property
    def cover_image(self):
        return self.images.filter(is_cover=True).first() or self.images.first()

    @property
    def public_latitude(self):
        return self._rounded_coordinate(self.latitude)

    @property
    def public_longitude(self):
        return self._rounded_coordinate(self.longitude)

    def _rounded_coordinate(self, value):
        """Degrade precision to ~1km when the supplier asked for approximate."""
        if value is None:
            return None
        if self.location_precision == self.LocationPrecision.EXACT:
            return value
        return round(float(value), 2)

    @property
    def map_url(self):
        """Google Maps deep link — no API key needed (section 14)."""
        lat, lng = self.public_latitude, self.public_longitude
        if lat is not None and lng is not None:
            return f"https://www.google.com/maps/search/?api=1&query={lat},{lng}"
        query = ", ".join(filter(None, [self.location, self.city, self.country]))
        if not query:
            return None
        from urllib.parse import quote_plus
        return f"https://www.google.com/maps/search/?api=1&query={quote_plus(query)}"

    def __str__(self):
        return f"{self.title} — {self.city}"


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="images"
    )
    image = models.ImageField(upload_to=product_image_upload_to)
    # The untouched upload, kept so a crop/rotation can always be redone from
    # the original instead of degrading an already-processed file.
    master = models.ImageField(upload_to=product_image_upload_to, blank=True, null=True)
    is_cover = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    width = models.PositiveIntegerField(default=0)
    height = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"Image #{self.pk} de {self.product_id}"


class ProductAttributeValue(models.Model):
    """Value of a `CategoryAttribute` for one product.

    Stored as JSON so a single row handles text, numbers, booleans, dates and
    multi-selects without a column per type. `numeric_value` is denormalised
    on save so range filters stay index-friendly in PostgreSQL.
    """

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="attribute_values")
    attribute = models.ForeignKey(CategoryAttribute, on_delete=models.CASCADE, related_name="values")
    value = models.JSONField(_("valeur"))
    numeric_value = models.FloatField(null=True, blank=True, db_index=True)

    class Meta:
        verbose_name = _("valeur d'attribut")
        verbose_name_plural = _("valeurs d'attribut")
        constraints = [
            models.UniqueConstraint(fields=["product", "attribute"], name="unique_value_per_product_attribute"),
        ]
        indexes = [models.Index(fields=["attribute", "numeric_value"])]

    def save(self, *args, **kwargs):
        self.numeric_value = None
        if self.attribute.attribute_type == CategoryAttribute.AttributeType.NUMBER:
            try:
                self.numeric_value = float(self.value)
            except (TypeError, ValueError):
                self.numeric_value = None
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.attribute.name}: {self.value}"


class Favorite(TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favorites"
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="favorited_by")

    class Meta:
        verbose_name = _("favori")
        verbose_name_plural = _("favoris")
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "product"], name="unique_favorite_per_user_product"),
        ]

    def __str__(self):
        return f"{self.user} ♥ {self.product}"
