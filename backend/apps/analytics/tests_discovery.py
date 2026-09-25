from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.catalog.models import Category, Favorite, Product
from apps.suppliers.models import SupplierProfile

from .models import ProductView, SearchEvent

User = get_user_model()


class DiscoveryApiTests(APITestCase):
    def setUp(self):
        self.cars = Category.objects.create(name="Voitures")
        self.tents = Category.objects.create(name="Tentes")
        self.supplier_user = User.objects.create_user(
            phone="+22670090001", password="pw", role=User.Role.SUPPLIER
        )
        self.visitor = User.objects.create_user(
            phone="+22670090002", password="pw", role=User.Role.VISITOR
        )
        self.profile = SupplierProfile.objects.get(user=self.supplier_user)

        self.viewed_car = self._product("Berline vue", self.cars, city="Ouagadougou", views=5)
        self.other_car = self._product("Autre berline", self.cars, city="Ouagadougou", views=50)
        self.tent = self._product("Tente", self.tents, city="Bobo", views=99)
        self._product("Brouillon", self.cars, status=Product.Status.PENDING)

    def _product(self, title, category, city="Bobo", views=0, status=Product.Status.APPROVED):
        return Product.objects.create(
            supplier=self.profile, category=category, title=title,
            price=1000, city=city, status=status, views_count=views,
        )

    def test_recently_viewed_is_ordered_and_deduplicated(self):
        self.client.force_authenticate(self.visitor)
        ProductView.objects.create(product=self.tent, user=self.visitor)
        ProductView.objects.create(product=self.viewed_car, user=self.visitor)
        ProductView.objects.create(product=self.tent, user=self.visitor)

        resp = self.client.get(reverse("api:discovery-me"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        titles = [p["title"] for p in resp.data["recently_viewed"]]
        self.assertEqual(titles, ["Tente", "Berline vue"])

    def test_recommendations_follow_viewed_category_and_exclude_seen(self):
        self.client.force_authenticate(self.visitor)
        ProductView.objects.create(product=self.viewed_car, user=self.visitor)

        resp = self.client.get(reverse("api:discovery-me"))
        titles = [p["title"] for p in resp.data["recommended"]]
        self.assertIn("Autre berline", titles)          # same category
        self.assertNotIn("Berline vue", titles)         # already seen
        self.assertNotIn("Brouillon", titles)           # not published

    def test_recommendations_fall_back_to_popular_for_new_visitor(self):
        resp = self.client.get(reverse("api:discovery-me"))
        titles = [p["title"] for p in resp.data["recommended"]]
        self.assertEqual(titles[0], "Tente")  # most viewed overall

    def test_supplier_does_not_get_recommended_their_own_products(self):
        self.client.force_authenticate(self.supplier_user)
        resp = self.client.get(reverse("api:discovery-me"))
        self.assertEqual(resp.data["recommended"], [])

    def test_recent_searches_are_deduplicated(self):
        self.client.force_authenticate(self.visitor)
        for query in ["tente", "tente", "voiture"]:
            SearchEvent.objects.create(
                user=self.visitor, query=query, normalized_query=query, results_count=3
            )
        resp = self.client.get(reverse("api:discovery-me"))
        queries = [s["normalized_query"] for s in resp.data["recent_searches"]]
        self.assertEqual(queries, ["voiture", "tente"])

    def test_favorites_influence_recommendations(self):
        self.client.force_authenticate(self.visitor)
        Favorite.objects.create(user=self.visitor, product=self.viewed_car)
        resp = self.client.get(reverse("api:discovery-me"))
        titles = [p["title"] for p in resp.data["recommended"]]
        self.assertIn("Autre berline", titles)
        self.assertNotIn("Berline vue", titles)  # already favourited

    def test_works_for_anonymous_visitors(self):
        resp = self.client.get(reverse("api:discovery-me"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["recently_viewed"], [])
        self.assertTrue(len(resp.data["new_arrivals"]) > 0)


class VisitorIdentityTests(APITestCase):
    """The anonymous id comes from a header, because SSR eats the cookie."""

    def setUp(self):
        self.category = Category.objects.create(name="Voitures")
        self.supplier_user = User.objects.create_user(
            phone="+22670091001", password="pw", role=User.Role.SUPPLIER
        )
        self.visitor = User.objects.create_user(
            phone="+22670091002", password="pw", role=User.Role.VISITOR
        )
        self.profile = SupplierProfile.objects.get(user=self.supplier_user)
        self.product = Product.objects.create(
            supplier=self.profile, category=self.category, title="Berline vue",
            price=1000, city="Bobo", status=Product.Status.APPROVED,
        )
        self.vid = "a" * 32

    def test_view_is_attributed_to_the_header_visitor(self):
        self.client.get(
            reverse("api:product-detail", args=[self.product.slug]),
            HTTP_X_VISITOR_ID=self.vid,
        )
        view = ProductView.objects.get(product=self.product)
        self.assertEqual(view.visitor_id, self.vid)

    def test_a_forged_visitor_id_is_discarded(self):
        self.client.get(
            reverse("api:product-detail", args=[self.product.slug]),
            HTTP_X_VISITOR_ID="../../etc/passwd",
        )
        view = ProductView.objects.get(product=self.product)
        self.assertNotEqual(view.visitor_id, "../../etc/passwd")
        self.assertRegex(view.visitor_id, r"^[0-9a-f]{32}$")

    def test_repeated_views_from_one_visitor_count_once(self):
        url = reverse("api:product-detail", args=[self.product.slug])
        self.client.get(url, HTTP_X_VISITOR_ID=self.vid)
        self.client.get(url, HTTP_X_VISITOR_ID=self.vid)
        self.assertEqual(ProductView.objects.filter(product=self.product).count(), 1)
        self.product.refresh_from_db()
        self.assertEqual(self.product.views_count, 1)

    def test_signed_in_visitor_sees_history_recorded_server_side(self):
        # SSR records the view without a user: only the visitor id links it.
        ProductView.objects.create(product=self.product, visitor_id=self.vid)
        self.client.force_authenticate(self.visitor)
        resp = self.client.get(reverse("api:discovery-me"), HTTP_X_VISITOR_ID=self.vid)
        titles = [p["title"] for p in resp.data["recently_viewed"]]
        self.assertIn("Berline vue", titles)

    def test_another_browser_does_not_see_that_history(self):
        ProductView.objects.create(product=self.product, visitor_id=self.vid)
        self.client.force_authenticate(self.visitor)
        resp = self.client.get(reverse("api:discovery-me"), HTTP_X_VISITOR_ID="b" * 32)
        self.assertEqual(resp.data["recently_viewed"], [])
