"""Media pipeline: processing, orphan cleanup, file deletion."""
import errno
import io
import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from PIL import Image as PILImage

from apps.catalog.models import Category, Product, ProductImage
from apps.media.models import MessageAttachment
from unittest.mock import patch
from django.core.files.storage import Storage
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from apps.media.processing import DISPLAY_SIZE, UnprocessableImage, render_image
from apps.messaging.models import Message
from apps.messaging.services import get_or_create_conversation
from apps.suppliers.models import SupplierProfile

User = get_user_model()
MEDIA = tempfile.mkdtemp(prefix="nogoya_media_tests_")


def jpeg_bytes(size=(2400, 1800), exif=None):
    buffer = io.BytesIO()
    image = PILImage.new("RGB", size, (10, 120, 200))
    image.save(buffer, format="JPEG", quality=95, exif=exif or b"")
    return buffer.getvalue()


@override_settings(MEDIA_ROOT=MEDIA)
class ImageProcessingTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(MEDIA, ignore_errors=True)
        super().tearDownClass()

    def test_renders_three_sizes_and_shrinks_the_file(self):
        original = jpeg_bytes()
        rendered = render_image(io.BytesIO(original))

        self.assertLessEqual(rendered["display_size"][0], DISPLAY_SIZE[0])
        self.assertLess(rendered["thumbnail_size"][0], rendered["display_size"][0])
        self.assertLess(
            len(rendered["display"].read()),
            len(original),
            "a processed image must be smaller than the upload",
        )

    def test_metadata_does_not_survive_processing(self):
        # What a phone actually attaches: the device it was taken with, plus
        # an orientation flag. Anything left here would be shared with the
        # picture — which is how a photo leaks where and how it was taken.
        exif = PILImage.Exif()
        exif[0x0112] = 6                       # orientation
        exif[0x010F] = "NoPhone"               # Make
        exif[0x0110] = "Model X"               # Model
        exif[0x010E] = "chez moi, 12°N 1°W"    # ImageDescription
        source = jpeg_bytes(exif=exif.tobytes())

        with PILImage.open(io.BytesIO(source)) as before:
            self.assertNotEqual(dict(before.getexif()), {}, "the fixture must carry EXIF")

        rendered = render_image(io.BytesIO(source))
        with PILImage.open(rendered["display"]) as stored:
            self.assertEqual(dict(stored.getexif()), {}, "no EXIF may reach storage")

    def test_orientation_is_applied_to_the_pixels(self):
        exif = PILImage.Exif()
        exif[0x0112] = 6  # "rotate 90° when displaying"
        rendered = render_image(io.BytesIO(jpeg_bytes(size=(400, 200), exif=exif.tobytes())))
        # Landscape in, portrait out: the flag was baked in, not dropped.
        self.assertGreater(rendered["display_size"][1], rendered["display_size"][0])

    def test_a_non_image_raises(self):
        with self.assertRaises(UnprocessableImage):
            render_image(io.BytesIO(b"<html>not an image</html>"))


@override_settings(MEDIA_ROOT=MEDIA)
class OrphanCleanupTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(MEDIA, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.supplier_user = User.objects.create_user(
            phone="+22670060001", password="pw", role=User.Role.SUPPLIER
        )
        self.visitor = User.objects.create_user(phone="+22670060002", password="pw")
        self.profile = SupplierProfile.objects.get(user=self.supplier_user)
        self.product = Product.objects.create(
            supplier=self.profile,
            category=Category.objects.create(name="Divers"),
            title="Tente", price=1000, city="Bobo", status=Product.Status.APPROVED,
        )
        self.conversation = get_or_create_conversation(
            self.visitor, self.supplier_user, product=self.product
        )[0]

    def _attachment(self):
        message = Message.objects.create(conversation=self.conversation, sender=self.visitor, body="x")
        attachment = MessageAttachment(message=message, kind="image", status="ready")
        attachment.file.save("photo.jpg", ContentFile(jpeg_bytes((10, 10))), save=False)
        attachment.poster.save("poster.jpg", ContentFile(jpeg_bytes((10, 10))), save=False)
        attachment.save()
        return attachment

    def test_deleting_an_attachment_removes_its_files(self):
        attachment = self._attachment()
        file_key, poster_key = attachment.file.name, attachment.poster.name
        self.assertTrue(default_storage.exists(file_key))

        attachment.delete()

        self.assertFalse(default_storage.exists(file_key), "the bytes must go with the row")
        self.assertFalse(default_storage.exists(poster_key))

    def test_deleting_a_message_removes_its_attachments_files(self):
        attachment = self._attachment()
        file_key = attachment.file.name

        attachment.message.delete()

        self.assertFalse(default_storage.exists(file_key))

    def test_prune_reports_orphans_without_deleting_by_default(self):
        default_storage.save("chat/999/999/stray.jpg", ContentFile(b"stray"))
        call_command("prune_media", "--hours", "0", verbosity=0)
        self.assertTrue(default_storage.exists("chat/999/999/stray.jpg"))

    def test_prune_deletes_orphans_when_asked(self):
        key = default_storage.save("chat/999/999/stray.jpg", ContentFile(b"stray"))
        call_command("prune_media", "--delete", "--hours", "0", verbosity=0)
        self.assertFalse(default_storage.exists(key))

    def test_prune_never_touches_a_referenced_file(self):
        attachment = self._attachment()
        image = ProductImage.objects.create(product=self.product, image=SimpleUploadedFile(
            "p.jpg", jpeg_bytes((10, 10)), content_type="image/jpeg"
        ))

        call_command("prune_media", "--delete", "--hours", "0", verbosity=0)

        self.assertTrue(default_storage.exists(attachment.file.name))
        self.assertTrue(default_storage.exists(attachment.poster.name))
        self.assertTrue(default_storage.exists(image.image.name))

    def test_prune_spares_recent_files(self):
        """An upload in flight belongs to a request that has not committed."""
        key = default_storage.save("chat/999/999/in-flight.jpg", ContentFile(b"x"))
        call_command("prune_media", "--delete", verbosity=0)  # default retention
        self.assertTrue(default_storage.exists(key))


class StorageFailureTests(APITestCase):
    """Ce que voit le vendeur quand le serveur, lui, est en cause.

    Disque plein, quota atteint, dossier média non inscriptible : rien de
    tout cela n'est la faute du fichier envoyé, et rien ne doit sortir en
    500 muet. Le message doit nommer la cause assez précisément pour que
    l'exploitant sache quoi aller corriger.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            phone="+22670080001", password="pw", role=User.Role.SUPPLIER
        )
        category = Category.objects.create(name="Tentes")
        self.product = Product.objects.create(
            supplier=self.user.supplier_profile, category=category,
            title="Tente", price=5000, city="Ouaga",
        )
        self.url = reverse("api:product-upload-images", args=[self.product.slug])
        self.client.force_authenticate(self.user)

    def _upload(self):
        return self.client.post(
            self.url,
            {"images": SimpleUploadedFile("photo.jpg", jpeg_bytes(), content_type="image/jpeg")},
            format="multipart",
        )

    def test_a_full_disk_is_reported_as_such_not_as_a_500(self):
        full = OSError(errno.ENOSPC, "No space left on device")
        with patch.object(Storage, "save", side_effect=full):
            response = self._upload()

        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertIn("espace disque insuffisant", response.data["images"][0])
        self.assertFalse(self.product.images.exists())

    def test_an_unwritable_media_directory_says_so(self):
        denied = OSError(errno.EACCES, "Permission denied")
        with patch.object(Storage, "save", side_effect=denied):
            response = self._upload()

        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertIn("non inscriptible", response.data["images"][0])

    def test_the_system_message_itself_is_never_echoed_to_the_client(self):
        """Le détail reste dans les journaux : la réponse dit la catégorie."""
        leaky = OSError(errno.ENOSPC, "No space left on device: '/home/binogoya/media'")
        with patch.object(Storage, "save", side_effect=leaky):
            response = self._upload()

        self.assertNotIn("/home/binogoya", str(response.data))

    def test_a_non_system_failure_still_names_its_category(self):
        """« OperationalError » oriente le diagnostic ; le message, non."""
        from django.db import DataError

        with patch.object(Storage, "save", side_effect=DataError("colonne trop courte")):
            response = self._upload()

        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertIn("DataError", response.data["images"][0])
        self.assertNotIn("colonne trop courte", str(response.data))

    def test_one_bad_file_does_not_cost_the_others(self):
        """Réussite partielle : ce qui est passé est rendu, le reste est nommé."""
        calls = {"n": 0}
        real_save = Storage.save

        def flaky(self, name, content, max_length=None):
            calls["n"] += 1
            if calls["n"] == 1:
                raise OSError(errno.ENOSPC, "No space left on device")
            return real_save(self, name, content, max_length)

        with patch.object(Storage, "save", flaky):
            response = self.client.post(
                self.url,
                {"images": [
                    SimpleUploadedFile("a.jpg", jpeg_bytes(), content_type="image/jpeg"),
                    SimpleUploadedFile("b.jpg", jpeg_bytes(), content_type="image/jpeg"),
                ]},
                format="multipart",
            )

        self.assertEqual(response.status_code, status.HTTP_207_MULTI_STATUS)
        self.assertEqual(len(response.data["images"]), 1)
        self.assertIn("a.jpg", response.data["failed"][0])


class UnwritableImageModeTests(TestCase):
    """Un mode que le JPEG refuse est une image invalide, pas une panne."""

    def test_a_16_bit_png_is_converted_instead_of_crashing(self):
        buffer = io.BytesIO()
        PILImage.new("I;16", (600, 400)).save(buffer, "PNG")

        rendered = render_image(io.BytesIO(buffer.getvalue()))
        self.assertEqual(rendered["master_size"], (600, 400))
