"""Favourites + dynamic category attributes (API level)."""
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.catalog.models import (
    Category,
    CategoryAttribute,
    Favorite,
    Product,
    ProductAttributeValue,
)
from apps.suppliers.models import SupplierProfile

User = get_user_model()


class FavoriteApiTests(APITestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Tentes")
        self.supplier_user = User.objects.create_user(
            phone="+22670040001", password="pw", role=User.Role.SUPPLIER
        )
        self.visitor = User.objects.create_user(
            phone="+22670040002", password="pw", role=User.Role.VISITOR
        )
        self.other = User.objects.create_user(
            phone="+22670040003", password="pw", role=User.Role.VISITOR
        )
        self.profile = SupplierProfile.objects.get(user=self.supplier_user)
        self.product = Product.objects.create(
            supplier=self.profile, category=self.category, title="Tente",
            price=5000, city="Bobo", status=Product.Status.APPROVED,
        )

    def test_toggle_favorite_adds_then_removes(self):
        self.client.force_authenticate(self.visitor)
        url = reverse("api:product-toggle-favorite", args=[self.product.slug])

        added = self.client.post(url)
        self.assertEqual(added.status_code, status.HTTP_201_CREATED)
        self.assertTrue(added.data["is_favorite"])
        self.assertEqual(Favorite.objects.count(), 1)

        removed = self.client.post(url)
        self.assertEqual(removed.status_code, status.HTTP_200_OK)
        self.assertFalse(removed.data["is_favorite"])
        self.assertEqual(Favorite.objects.count(), 0)

    def test_favorite_requires_authentication(self):
        resp = self.client.post(reverse("api:product-toggle-favorite", args=[self.product.slug]))
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_favorites_list_is_scoped_to_owner(self):
        Favorite.objects.create(user=self.visitor, product=self.product)

        self.client.force_authenticate(self.visitor)
        mine = self.client.get(reverse("api:favorite-list"))
        self.assertEqual(mine.data["count"], 1)
        self.assertEqual(mine.data["results"][0]["product"]["slug"], self.product.slug)

        self.client.force_authenticate(self.other)
        theirs = self.client.get(reverse("api:favorite-list"))
        self.assertEqual(theirs.data["count"], 0)

    def test_favorite_slugs_are_scoped_to_the_requester(self):
        # The hearts on server-rendered pages reconcile with this endpoint.
        Favorite.objects.create(user=self.visitor, product=self.product)
        url = reverse("api:favorite-slugs")

        self.client.force_authenticate(self.visitor)
        mine = self.client.get(url)
        self.assertEqual(mine.status_code, status.HTTP_200_OK)
        self.assertEqual(mine.data["slugs"], [self.product.slug])

        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get(url).data["slugs"], [])

        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(url).status_code, status.HTTP_401_UNAUTHORIZED)

    def test_cannot_delete_someone_elses_favorite(self):
        favorite = Favorite.objects.create(user=self.visitor, product=self.product)
        self.client.force_authenticate(self.other)
        resp = self.client.delete(reverse("api:favorite-detail", args=[favorite.pk]))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Favorite.objects.filter(pk=favorite.pk).exists())

    def test_product_list_exposes_is_favorite(self):
        Favorite.objects.create(user=self.visitor, product=self.product)
        self.client.force_authenticate(self.visitor)
        resp = self.client.get(reverse("api:product-list"))
        self.assertTrue(resp.data["results"][0]["is_favorite"])

    def test_favorites_filter_on_product_list(self):
        Favorite.objects.create(user=self.visitor, product=self.product)
        Product.objects.create(
            supplier=self.profile, category=self.category, title="Autre",
            price=1000, city="Bobo", status=Product.Status.APPROVED,
        )
        self.client.force_authenticate(self.visitor)
        resp = self.client.get(reverse("api:product-list") + "?favorites=true")
        self.assertEqual(resp.data["count"], 1)


class DynamicAttributeApiTests(APITestCase):
    def setUp(self):
        self.parent = Category.objects.create(name="Véhicules")
        self.category = Category.objects.create(name="Voitures", parent=self.parent)
        self.brand = CategoryAttribute.objects.create(
            category=self.category, name="Marque", attribute_type="text", required=True, position=0
        )
        self.year = CategoryAttribute.objects.create(
            category=self.category, name="Année", attribute_type="number", filterable=True, position=1
        )
        self.fuel = CategoryAttribute.objects.create(
            category=self.category, name="Carburant", attribute_type="select",
            options=["Essence", "Diesel"], filterable=True, position=2,
        )
        # Declared on the parent: sub-categories inherit it.
        self.shared = CategoryAttribute.objects.create(
            category=self.parent, name="Kilométrage", attribute_type="number", unit="km", position=3
        )
        self.supplier_user = User.objects.create_user(
            phone="+22670041001", password="pw", role=User.Role.SUPPLIER
        )
        self.profile = SupplierProfile.objects.get(user=self.supplier_user)

    def _payload(self, **over):
        data = {
            "title": "Berline 2019", "category": self.category.pk,
            "description": "Bonne voiture familiale", "price": "4500000",
            "listing_type": "sale", "rental_period": "none", "city": "Ouagadougou",
            "attributes": {"marque": "Toyota", "annee": 2019, "carburant": "Diesel"},
        }
        data.update(over)
        return data

    def test_category_endpoint_exposes_inherited_attributes(self):
        resp = self.client.get(reverse("api:category-list"))
        vehicles = next(c for c in resp.data if c["slug"] == "vehicules")
        cars = next(c for c in vehicles["children"] if c["slug"] == "voitures")
        slugs = [a["slug"] for a in cars["attributes"]]
        self.assertIn("marque", slugs)
        self.assertIn("kilometrage", slugs)  # inherited from Véhicules

    def test_create_product_with_attributes(self):
        self.client.force_authenticate(self.supplier_user)
        resp = self.client.post(reverse("api:product-list"), self._payload(), format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)

        product = Product.objects.get(title="Berline 2019")
        values = {v.attribute.slug: v.value for v in product.attribute_values.all()}
        self.assertEqual(values["marque"], "Toyota")
        self.assertEqual(values["annee"], 2019.0)
        self.assertEqual(values["carburant"], "Diesel")
        # numeric_value is denormalised for range filtering
        self.assertEqual(
            ProductAttributeValue.objects.get(product=product, attribute=self.year).numeric_value,
            2019.0,
        )

    def test_required_attribute_is_enforced(self):
        self.client.force_authenticate(self.supplier_user)
        payload = self._payload(attributes={"annee": 2019})
        resp = self.client.post(reverse("api:product-list"), payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("marque", str(resp.data))

    def test_invalid_select_option_rejected(self):
        self.client.force_authenticate(self.supplier_user)
        payload = self._payload(attributes={"marque": "Toyota", "carburant": "Kérosène"})
        resp = self.client.post(reverse("api:product-list"), payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unknown_attribute_rejected(self):
        self.client.force_authenticate(self.supplier_user)
        payload = self._payload(attributes={"marque": "Toyota", "couleur": "Rouge"})
        resp = self.client.post(reverse("api:product-list"), payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("couleur", str(resp.data))

    def test_non_numeric_value_rejected_for_number_attribute(self):
        self.client.force_authenticate(self.supplier_user)
        payload = self._payload(attributes={"marque": "Toyota", "annee": "l'an dernier"})
        resp = self.client.post(reverse("api:product-list"), payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_attributes_are_replaced_on_update_and_returned_on_detail(self):
        self.client.force_authenticate(self.supplier_user)
        create = self.client.post(reverse("api:product-list"), self._payload(), format="json")
        slug = create.data["slug"]

        self.client.patch(
            reverse("api:product-detail", args=[slug]),
            {"attributes": {"marque": "Peugeot", "annee": 2021}},
            format="json",
        )
        product = Product.objects.get(slug=slug)
        values = {v.attribute.slug: v.value for v in product.attribute_values.all()}
        self.assertEqual(values["marque"], "Peugeot")
        self.assertNotIn("carburant", values)  # dropped, it was not resent

        Product.objects.filter(slug=slug).update(status=Product.Status.APPROVED)
        detail = self.client.get(reverse("api:product-detail", args=[slug]))
        returned = {a["slug"]: a["value"] for a in detail.data["attributes"]}
        self.assertEqual(returned["marque"], "Peugeot")

    def test_filter_products_by_attribute(self):
        self.client.force_authenticate(self.supplier_user)
        first = self.client.post(reverse("api:product-list"), self._payload(), format="json")
        second = self.client.post(
            reverse("api:product-list"),
            self._payload(title="Citadine 2015", attributes={"marque": "Kia", "annee": 2015, "carburant": "Essence"}),
            format="json",
        )
        Product.objects.filter(slug__in=[first.data["slug"], second.data["slug"]]).update(
            status=Product.Status.APPROVED
        )

        self.client.force_authenticate(None)
        diesel = self.client.get(reverse("api:product-list") + "?attr_carburant=Diesel")
        self.assertEqual(diesel.data["count"], 1)
        self.assertEqual(diesel.data["results"][0]["title"], "Berline 2019")

        recent = self.client.get(reverse("api:product-list") + "?attr_annee_min=2018")
        self.assertEqual(recent.data["count"], 1)

        everything = self.client.get(reverse("api:product-list"))
        self.assertEqual(everything.data["count"], 2)

    def test_non_filterable_attribute_is_ignored_as_filter(self):
        """`marque` is not marked filterable: it must not narrow results."""
        self.client.force_authenticate(self.supplier_user)
        created = self.client.post(reverse("api:product-list"), self._payload(), format="json")
        Product.objects.filter(slug=created.data["slug"]).update(status=Product.Status.APPROVED)

        self.client.force_authenticate(None)
        resp = self.client.get(reverse("api:product-list") + "?attr_marque=Renault")
        self.assertEqual(resp.data["count"], 1)
