from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.catalog.models import Category, Product
from apps.suppliers.models import SupplierProfile

from .models import LiveProduct, LiveSession

User = get_user_model()


class LiveSessionApiTests(APITestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Électronique")
        self.host = User.objects.create_user(
            phone="+22670070001", password="pw", role=User.Role.SUPPLIER
        )
        self.other_supplier = User.objects.create_user(
            phone="+22670070002", password="pw", role=User.Role.SUPPLIER
        )
        self.viewer = User.objects.create_user(
            phone="+22670070003", password="pw", role=User.Role.VISITOR
        )
        self.host_profile = SupplierProfile.objects.get(user=self.host)
        self.other_profile = SupplierProfile.objects.get(user=self.other_supplier)
        self.product = Product.objects.create(
            supplier=self.host_profile, category=self.category, title="Caméra Sony",
            price=25000, city="Ouagadougou", status=Product.Status.APPROVED,
        )
        self.foreign_product = Product.objects.create(
            supplier=self.other_profile, category=self.category, title="Objectif",
            price=15000, city="Bobo", status=Product.Status.APPROVED,
        )

    def _create_live(self, user=None):
        self.client.force_authenticate(user or self.host)
        return self.client.post(
            reverse("api:live-list"), {"title": "Présentation matériel", "description": "Démo"}
        )

    def test_create_live_defaults_to_draft_owned_by_host(self):
        resp = self._create_live()
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        live = LiveSession.objects.get(pk=resp.data["id"])
        self.assertEqual(live.host, self.host)
        self.assertEqual(live.status, LiveSession.Status.DRAFT)
        # The write payload is narrow; the response must still describe the
        # session fully so the client needs no extra round trip.
        self.assertEqual(resp.data["status"], LiveSession.Status.DRAFT)
        self.assertEqual(resp.data["host"]["id"], self.host.id)
        self.assertEqual(resp.data["live_products"], [])

    def test_drafts_are_hidden_from_the_public_list(self):
        self._create_live()
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(reverse("api:live-list")).data["count"], 0)

        self.client.force_authenticate(self.host)
        mine = self.client.get(reverse("api:live-list") + "?mine=true")
        self.assertEqual(mine.data["count"], 1)

    def test_only_host_can_start_and_end(self):
        live_id = self._create_live().data["id"]

        self.client.force_authenticate(self.other_supplier)
        forbidden = self.client.post(reverse("api:live-start", args=[live_id]))
        self.assertEqual(forbidden.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(self.host)
        started = self.client.post(reverse("api:live-start", args=[live_id]))
        self.assertEqual(started.status_code, status.HTTP_200_OK)
        self.assertEqual(started.data["status"], "live")

        ended = self.client.post(reverse("api:live-end", args=[live_id]))
        self.assertEqual(ended.data["status"], "ended")
        self.assertIsNotNone(ended.data["ended_at"])

    def test_host_attaches_own_products_only(self):
        live_id = self._create_live().data["id"]
        url = reverse("api:live-products", args=[live_id])

        ok = self.client.post(url, {"product": self.product.pk})
        self.assertEqual(ok.status_code, status.HTTP_201_CREATED, ok.data)
        self.assertEqual(ok.data["product"]["title"], "Caméra Sony")

        forbidden = self.client.post(url, {"product": self.foreign_product.pk})
        self.assertEqual(forbidden.status_code, status.HTTP_403_FORBIDDEN)

        # attaching twice does not duplicate the link
        self.client.post(url, {"product": self.product.pk})
        self.assertEqual(LiveProduct.objects.filter(live_id=live_id).count(), 1)

    def test_pin_and_unpin_product(self):
        live_id = self._create_live().data["id"]
        self.client.post(reverse("api:live-products", args=[live_id]), {"product": self.product.pk})

        pinned = self.client.post(
            reverse("api:live-pin-product", args=[live_id, self.product.pk])
        )
        self.assertEqual(pinned.status_code, status.HTTP_200_OK)
        self.assertTrue(pinned.data["is_featured"])

        unpinned = self.client.post(
            reverse("api:live-unpin-product", args=[live_id, self.product.pk])
        )
        self.assertFalse(unpinned.data["is_featured"])

    def test_only_one_featured_product_at_a_time(self):
        live_id = self._create_live().data["id"]
        second = Product.objects.create(
            supplier=self.host_profile, category=self.category, title="Trépied",
            price=5000, city="Ouagadougou", status=Product.Status.APPROVED,
        )
        for product in (self.product, second):
            self.client.post(reverse("api:live-products", args=[live_id]), {"product": product.pk})
            self.client.post(reverse("api:live-pin-product", args=[live_id, product.pk]))

        featured = LiveProduct.objects.filter(live_id=live_id, is_featured=True)
        self.assertEqual(featured.count(), 1)
        self.assertEqual(featured.first().product_id, second.pk)

    def test_join_leave_and_viewer_count(self):
        live_id = self._create_live().data["id"]
        self.client.post(reverse("api:live-start", args=[live_id]))

        self.client.force_authenticate(self.viewer)
        joined = self.client.post(reverse("api:live-join", args=[live_id]))
        self.assertEqual(joined.data["viewers"], 1)

        left = self.client.post(reverse("api:live-leave", args=[live_id]))
        self.assertEqual(left.data["viewers"], 0)

        live = LiveSession.objects.get(pk=live_id)
        self.assertEqual(live.peak_viewers, 1)

    def test_cannot_join_a_live_that_is_not_running(self):
        live_id = self._create_live().data["id"]
        self.client.force_authenticate(self.viewer)
        resp = self.client.post(reverse("api:live-join", args=[live_id]))
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_live_chat_messages(self):
        live_id = self._create_live().data["id"]
        self.client.post(reverse("api:live-start", args=[live_id]))

        self.client.force_authenticate(self.viewer)
        sent = self.client.post(
            reverse("api:live-messages", args=[live_id]), {"message": "Combien pour la caméra ?"}
        )
        self.assertEqual(sent.status_code, status.HTTP_201_CREATED, sent.data)
        self.assertEqual(sent.data["sender"]["id"], self.viewer.id)

        listing = self.client.get(reverse("api:live-messages", args=[live_id]))
        self.assertEqual(listing.data["count"], 1)
