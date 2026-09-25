from datetime import timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.catalog.models import Category, Product
from apps.suppliers.models import SupplierProfile

from .models import ContactEvent, ProductView

User = get_user_model()


class SupplierAnalyticsTests(APITestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Tentes")
        self.supplier_user = User.objects.create_user(
            phone="+22670080001", password="pw", role=User.Role.SUPPLIER
        )
        self.other_supplier = User.objects.create_user(
            phone="+22670080002", password="pw", role=User.Role.SUPPLIER
        )
        self.visitor = User.objects.create_user(
            phone="+22670080003", password="pw", role=User.Role.VISITOR
        )
        self.profile = SupplierProfile.objects.get(user=self.supplier_user)
        self.other_profile = SupplierProfile.objects.get(user=self.other_supplier)

        self.product = Product.objects.create(
            supplier=self.profile, category=self.category, title="Tente",
            price=5000, city="Bobo", status=Product.Status.APPROVED, views_count=42,
        )
        Product.objects.create(
            supplier=self.profile, category=self.category, title="Brouillon",
            price=1000, city="Bobo",
        )
        self.foreign_product = Product.objects.create(
            supplier=self.other_profile, category=self.category, title="Pas à moi",
            price=1000, city="Bobo", status=Product.Status.APPROVED,
        )

        ProductView.objects.create(product=self.product, user=self.visitor)
        ProductView.objects.create(product=self.product, visitor_id="abc")
        ContactEvent.objects.create(product=self.product, user=self.visitor, channel="phone")
        # noise belonging to another supplier — must never show up
        ProductView.objects.create(product=self.foreign_product, visitor_id="zzz")
        ContactEvent.objects.create(product=self.foreign_product, user=self.visitor)

    def test_analytics_returns_one_point_per_day_including_zeros(self):
        self.client.force_authenticate(self.supplier_user)
        resp = self.client.get(reverse("api:supplier-analytics") + "?days=7")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data["views"]), 7)
        self.assertEqual(len(resp.data["contacts"]), 7)
        self.assertEqual(len(resp.data["messages"]), 7)

        today = timezone.localdate().isoformat()
        today_views = next(p for p in resp.data["views"] if p["date"] == today)
        self.assertEqual(today_views["value"], 2)
        yesterday = (timezone.localdate() - timedelta(days=1)).isoformat()
        self.assertEqual(next(p for p in resp.data["views"] if p["date"] == yesterday)["value"], 0)

    def test_analytics_only_covers_own_products(self):
        self.client.force_authenticate(self.supplier_user)
        resp = self.client.get(reverse("api:supplier-analytics"))
        total_views = sum(p["value"] for p in resp.data["views"])
        self.assertEqual(total_views, 2)  # the foreign product's view is excluded
        total_contacts = sum(p["value"] for p in resp.data["contacts"])
        self.assertEqual(total_contacts, 1)
        titles = [p["title"] for p in resp.data["top_products"]]
        self.assertNotIn("Pas à moi", titles)

    def test_products_breakdown_and_top_products(self):
        self.client.force_authenticate(self.supplier_user)
        resp = self.client.get(reverse("api:supplier-analytics"))
        self.assertEqual(resp.data["products_breakdown"]["online"], 1)
        self.assertEqual(resp.data["products_breakdown"]["pending"], 1)
        self.assertEqual(resp.data["top_products"][0]["title"], "Tente")
        self.assertEqual(resp.data["top_products"][0]["views_count"], 42)

    def test_days_parameter_is_clamped(self):
        self.client.force_authenticate(self.supplier_user)
        self.assertEqual(len(self.client.get(reverse("api:supplier-analytics") + "?days=1").data["views"]), 7)
        self.assertEqual(len(self.client.get(reverse("api:supplier-analytics") + "?days=9999").data["views"]), 365)
        self.assertEqual(len(self.client.get(reverse("api:supplier-analytics") + "?days=abc").data["views"]), 30)

    def test_requires_a_supplier_account(self):
        self.client.force_authenticate(self.visitor)
        resp = self.client.get(reverse("api:supplier-analytics"))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_requires_authentication(self):
        resp = self.client.get(reverse("api:supplier-analytics"))
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)
