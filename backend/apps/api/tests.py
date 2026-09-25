import io
import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from PIL import Image as PILImage
from rest_framework import status
from rest_framework.test import APITestCase

from apps.catalog.models import Category, Product
from apps.suppliers.models import SupplierProfile

User = get_user_model()
MEDIA = tempfile.mkdtemp(prefix="nogoya_api_test_media_")


def make_image(name="photo.jpg", size=(60, 40)):
    buf = io.BytesIO()
    PILImage.new("RGB", size, (200, 100, 50)).save(buf, format="JPEG")
    buf.seek(0)
    return SimpleUploadedFile(name, buf.read(), content_type="image/jpeg")


class AuthApiTests(APITestCase):
    def test_register_visitor(self):
        resp = self.client.post(reverse("api:auth-register"), {
            "phone": "+22670001111",
            "first_name": "Awa",
            "last_name": "Traoré",
            "role": "visitor",
            "password": "UnMotDePasseSolide9",
            "password2": "UnMotDePasseSolide9",
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        user = User.objects.get(phone="+22670001111")
        self.assertEqual(user.role, User.Role.VISITOR)
        self.assertNotIn("password", resp.data)

    def test_register_supplier_creates_profile(self):
        resp = self.client.post(reverse("api:auth-register"), {
            "phone": "+22670001112",
            "first_name": "Issa",
            "last_name": "Ouédraogo",
            "role": "supplier",
            "password": "UnMotDePasseSolide9",
            "password2": "UnMotDePasseSolide9",
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        user = User.objects.get(phone="+22670001112")
        self.assertTrue(SupplierProfile.objects.filter(user=user).exists())

    def test_register_rejects_weak_password(self):
        resp = self.client.post(reverse("api:auth-register"), {
            "phone": "+22670001113", "first_name": "A", "last_name": "B",
            "role": "visitor", "password": "1234", "password2": "1234",
        })
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(phone="+22670001113").exists())

    def test_register_rejects_duplicate_phone(self):
        User.objects.create_user(phone="+22670001114", password="pw")
        resp = self.client.post(reverse("api:auth-register"), {
            "phone": "+22670001114", "first_name": "A", "last_name": "B",
            "role": "visitor", "password": "UnMotDePasseSolide9", "password2": "UnMotDePasseSolide9",
        })
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_returns_tokens_and_wrong_password_rejected(self):
        User.objects.create_user(phone="+22670001115", password="UnMotDePasseSolide9")
        ok = self.client.post(reverse("api:auth-login"), {
            "phone": "+22670001115", "password": "UnMotDePasseSolide9",
        })
        self.assertEqual(ok.status_code, status.HTTP_200_OK)
        self.assertIn("access", ok.data)
        self.assertIn("refresh", ok.data)
        self.assertEqual(ok.data["user"]["role"], User.Role.VISITOR)

        bad = self.client.post(reverse("api:auth-login"), {
            "phone": "+22670001115", "password": "wrong",
        })
        self.assertEqual(bad.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_requires_auth_then_returns_and_updates_profile(self):
        user = User.objects.create_user(phone="+22670001116", password="pw")
        anon = self.client.get(reverse("api:auth-me"))
        self.assertEqual(anon.status_code, status.HTTP_401_UNAUTHORIZED)

        self.client.force_authenticate(user)
        resp = self.client.get(reverse("api:auth-me"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["phone"], "+22670001116")

        patched = self.client.patch(reverse("api:auth-me"), {"first_name": "Nouveau"})
        self.assertEqual(patched.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertEqual(user.first_name, "Nouveau")

    def test_me_cannot_escalate_role(self):
        user = User.objects.create_user(phone="+22670001117", password="pw", role=User.Role.VISITOR)
        self.client.force_authenticate(user)
        self.client.patch(reverse("api:auth-me"), {"role": "supplier"})
        user.refresh_from_db()
        self.assertEqual(user.role, User.Role.VISITOR)


@override_settings(MEDIA_ROOT=MEDIA)
class CatalogApiTests(APITestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(MEDIA, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        cache.clear()
        self.parent = Category.objects.create(name="Événementiel")
        self.leaf = Category.objects.create(name="Chaises", parent=self.parent)
        self.supplier_user = User.objects.create_user(
            phone="+22670002001", password="pw", role=User.Role.SUPPLIER
        )
        self.other_supplier = User.objects.create_user(
            phone="+22670002002", password="pw", role=User.Role.SUPPLIER
        )
        self.visitor = User.objects.create_user(
            phone="+22670002003", password="pw", role=User.Role.VISITOR
        )
        self.profile = SupplierProfile.objects.get(user=self.supplier_user)
        self.other_profile = SupplierProfile.objects.get(user=self.other_supplier)

    def _payload(self, **over):
        data = {
            "title": "Chaises pliantes", "category": self.leaf.pk,
            "description": "Lot de 50", "price": "1500", "currency": "XOF",
            "listing_type": "rent", "rental_period": "day", "city": "Ouagadougou",
        }
        data.update(over)
        return data

    def test_category_list_nests_children(self):
        resp = self.client.get(reverse("api:category-list"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]["slug"], "evenementiel")
        self.assertEqual(resp.data[0]["children"][0]["slug"], "chaises")

    def test_visitor_cannot_create_product(self):
        self.client.force_authenticate(self.visitor)
        resp = self.client.post(reverse("api:product-list"), self._payload())
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_supplier_creates_product_pending_and_hidden_from_public_list(self):
        self.client.force_authenticate(self.supplier_user)
        resp = self.client.post(reverse("api:product-list"), self._payload())
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        product = Product.objects.get(title="Chaises pliantes")
        self.assertEqual(product.status, Product.Status.PENDING)
        self.assertEqual(product.supplier, self.profile)
        # the frontend immediately follows up with an upload_images call using
        # this slug, so the create response must return it.
        self.assertEqual(resp.data["slug"], product.slug)

        public_list = self.client.get(reverse("api:product-list"))
        self.assertEqual(public_list.data["count"], 0)

        mine = self.client.get(reverse("api:product-list") + "?mine=true")
        self.assertEqual(mine.data["count"], 1)

    def test_pending_product_detail_hidden_from_others_but_visible_to_owner(self):
        product = Product.objects.create(
            supplier=self.profile, category=self.leaf, title="Tente",
            price=5000, city="Bobo",
        )
        self.client.force_authenticate(self.other_supplier)
        resp = self.client.get(reverse("api:product-detail", args=[product.slug]))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

        self.client.force_authenticate(self.supplier_user)
        resp = self.client.get(reverse("api:product-detail", args=[product.slug]))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_non_owner_cannot_update_or_delete(self):
        product = Product.objects.create(
            supplier=self.profile, category=self.leaf, title="Tente",
            price=5000, city="Bobo", status=Product.Status.APPROVED,
        )
        self.client.force_authenticate(self.other_supplier)
        resp = self.client.patch(reverse("api:product-detail", args=[product.slug]), {"title": "Hack"})
        self.assertIn(resp.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND))
        product.refresh_from_db()
        self.assertEqual(product.title, "Tente")

        resp = self.client.delete(reverse("api:product-detail", args=[product.slug]))
        self.assertIn(resp.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND))
        self.assertTrue(Product.objects.filter(pk=product.pk).exists())

    def test_owner_update_resets_to_pending(self):
        product = Product.objects.create(
            supplier=self.profile, category=self.leaf, title="Tente",
            price=5000, city="Bobo", status=Product.Status.APPROVED,
        )
        self.client.force_authenticate(self.supplier_user)
        resp = self.client.patch(reverse("api:product-detail", args=[product.slug]), {"title": "Tente 10m"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        product.refresh_from_db()
        self.assertEqual(product.title, "Tente 10m")
        self.assertEqual(product.status, Product.Status.PENDING)

    def test_image_upload_sets_cover_and_only_owner_may_upload(self):
        product = Product.objects.create(
            supplier=self.profile, category=self.leaf, title="Tente",
            price=5000, city="Bobo", status=Product.Status.APPROVED,
        )
        self.client.force_authenticate(self.other_supplier)
        forbidden = self.client.post(
            reverse("api:product-upload-images", args=[product.slug]),
            {"images": make_image()}, format="multipart",
        )
        self.assertIn(forbidden.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND))

        self.client.force_authenticate(self.supplier_user)
        resp = self.client.post(
            reverse("api:product-upload-images", args=[product.slug]),
            {"images": [make_image("a.jpg"), make_image("b.jpg")]}, format="multipart",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        self.assertEqual(len(resp.data), 2)
        self.assertTrue(resp.data[0]["is_cover"])
        self.assertFalse(resp.data[1]["is_cover"])

    def test_view_count_deduped_per_visitor(self):
        product = Product.objects.create(
            supplier=self.profile, category=self.leaf, title="Tente",
            price=5000, city="Bobo", status=Product.Status.APPROVED,
        )
        url = reverse("api:product-detail", args=[product.slug])
        self.client.get(url)
        self.client.get(url)
        product.refresh_from_db()
        self.assertEqual(product.views_count, 1)

    def test_owner_can_toggle_active_but_not_others(self):
        product = Product.objects.create(
            supplier=self.profile, category=self.leaf, title="Tente",
            price=5000, city="Bobo", status=Product.Status.APPROVED,
        )
        self.assertTrue(product.is_active)

        self.client.force_authenticate(self.other_supplier)
        forbidden = self.client.post(reverse("api:product-toggle-active", args=[product.slug]))
        self.assertIn(forbidden.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND))

        self.client.force_authenticate(self.supplier_user)
        resp = self.client.post(reverse("api:product-toggle-active", args=[product.slug]))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        product.refresh_from_db()
        self.assertFalse(product.is_active)

        # unpublished products disappear from the public list...
        self.client.force_authenticate(None)
        public_list = self.client.get(reverse("api:product-list"))
        self.assertEqual(public_list.data["count"], 0)
        # ...and 404 for anyone but the owner.
        hidden = self.client.get(reverse("api:product-detail", args=[product.slug]))
        self.assertEqual(hidden.status_code, status.HTTP_404_NOT_FOUND)

    def test_pending_product_cannot_be_toggled(self):
        product = Product.objects.create(
            supplier=self.profile, category=self.leaf, title="Tente",
            price=5000, city="Bobo",
        )
        self.client.force_authenticate(self.supplier_user)
        resp = self.client.post(reverse("api:product-toggle-active", args=[product.slug]))
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_approximate_location_rounds_coordinates_and_exact_does_not(self):
        approx = Product.objects.create(
            supplier=self.profile, category=self.leaf, title="Tente approx",
            price=5000, city="Bobo", status=Product.Status.APPROVED,
            latitude="11.178900", longitude="-4.297200",
            location_precision=Product.LocationPrecision.APPROXIMATE,
        )
        exact = Product.objects.create(
            supplier=self.profile, category=self.leaf, title="Tente exacte",
            price=5000, city="Bobo", status=Product.Status.APPROVED,
            latitude="11.178900", longitude="-4.297200",
            location_precision=Product.LocationPrecision.EXACT,
        )
        resp_approx = self.client.get(reverse("api:product-detail", args=[approx.slug]))
        resp_exact = self.client.get(reverse("api:product-detail", args=[exact.slug]))
        self.assertEqual(resp_approx.data["latitude"], 11.18)
        self.assertEqual(float(resp_exact.data["latitude"]), 11.1789)
        self.assertIsNotNone(resp_exact.data["map_url"])

    def test_map_url_falls_back_to_address_without_coordinates(self):
        product = Product.objects.create(
            supplier=self.profile, category=self.leaf, title="Sans coordonnées",
            price=5000, city="Ouagadougou", status=Product.Status.APPROVED,
        )
        resp = self.client.get(reverse("api:product-detail", args=[product.slug]))
        self.assertIn("Ouagadougou", resp.data["map_url"])

    def test_contact_action_reveals_and_logs_only_for_non_owner(self):
        product = Product.objects.create(
            supplier=self.profile, category=self.leaf, title="Tente",
            price=5000, city="Bobo", status=Product.Status.APPROVED,
        )
        self.client.force_authenticate(self.visitor)
        resp = self.client.post(reverse("api:product-contact", args=[product.slug]), {"channel": "phone"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["phone"], self.supplier_user.phone)
        from apps.analytics.models import ContactEvent
        self.assertEqual(ContactEvent.objects.filter(product=product).count(), 1)

        # the owner checking their own contact info shouldn't self-count
        self.client.force_authenticate(self.supplier_user)
        self.client.post(reverse("api:product-contact", args=[product.slug]))
        self.assertEqual(ContactEvent.objects.filter(product=product).count(), 1)

    def test_share_action_increments_counter_anonymously(self):
        product = Product.objects.create(
            supplier=self.profile, category=self.leaf, title="Tente",
            price=5000, city="Bobo", status=Product.Status.APPROVED,
        )
        resp = self.client.post(reverse("api:product-share", args=[product.slug]))
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        product.refresh_from_db()
        self.assertEqual(product.shares_count, 1)

    def test_supplier_stats(self):
        Product.objects.create(
            supplier=self.profile, category=self.leaf, title="En ligne",
            price=1000, city="Bobo", status=Product.Status.APPROVED, views_count=10,
        )
        Product.objects.create(
            supplier=self.profile, category=self.leaf, title="En attente",
            price=1000, city="Bobo",
        )
        self.client.force_authenticate(self.supplier_user)
        resp = self.client.get(reverse("api:supplier-stats"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["products_online"], 1)
        self.assertEqual(resp.data["products_total"], 2)
        self.assertEqual(resp.data["total_views"], 10)

    def test_owner_viewing_own_product_does_not_count(self):
        product = Product.objects.create(
            supplier=self.profile, category=self.leaf, title="Tente",
            price=5000, city="Bobo", status=Product.Status.APPROVED,
        )
        self.client.force_authenticate(self.supplier_user)
        self.client.get(reverse("api:product-detail", args=[product.slug]))
        product.refresh_from_db()
        self.assertEqual(product.views_count, 0)
