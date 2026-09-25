"""Chat attachments: upload, validation, compression, access control.

Covers the three kinds a conversation carries (image, video, voice note) and
the rules that protect them: only participants read them, only plausible
files are stored, and nothing reaches the bucket before it is checked.
"""
import io
import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from PIL import Image as PILImage
from rest_framework import status
from rest_framework.test import APITestCase

from apps.catalog.models import Category, Product
from apps.media.models import MessageAttachment
from apps.notifications.models import Notification
from apps.suppliers.models import SupplierProfile


User = get_user_model()
MEDIA = tempfile.mkdtemp(prefix="nogoya_chat_media_")

# Minimal valid-looking containers — enough for the magic-byte checks.
WEBM_BYTES = b"\x1a\x45\xdf\xa3" + b"\x00" * 512
MP4_BYTES = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 512


def jpeg_upload(name="photo.jpg", size=(1200, 900), exif_gps=False):
    buffer = io.BytesIO()
    image = PILImage.new("RGB", size, (120, 60, 200))
    image.save(buffer, format="JPEG", quality=95)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/jpeg")


def audio_upload(name="voice.webm", content=WEBM_BYTES, content_type="audio/webm"):
    return SimpleUploadedFile(name, content, content_type=content_type)


def video_upload(name="clip.mp4", content=MP4_BYTES, content_type="video/mp4"):
    return SimpleUploadedFile(name, content, content_type=content_type)


@override_settings(MEDIA_ROOT=MEDIA)
class ChatAttachmentTests(APITestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(MEDIA, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.category = Category.objects.create(name="Tentes")
        self.supplier_user = User.objects.create_user(
            phone="+22670050001", password="pw", role=User.Role.SUPPLIER
        )
        self.visitor = User.objects.create_user(
            phone="+22670050002", password="pw", role=User.Role.VISITOR
        )
        self.outsider = User.objects.create_user(
            phone="+22670050003", password="pw", role=User.Role.VISITOR
        )
        self.profile = SupplierProfile.objects.get(user=self.supplier_user)
        self.product = Product.objects.create(
            supplier=self.profile, category=self.category, title="Tente",
            price=5000, city="Bobo", status=Product.Status.APPROVED,
        )
        self.client.force_authenticate(self.visitor)
        self.conversation_id = self.client.post(
            reverse("api:conversation-list"), {"product": self.product.pk}
        ).data["id"]

    def _post(self, payload):
        return self.client.post(
            reverse("api:conversation-messages", args=[self.conversation_id]),
            payload,
            format="multipart",
        )

    def _attachment_url(self, message_id, attachment_id, suffix=""):
        name = "api:conversation-attachment-poster" if suffix else "api:conversation-attachment"
        return reverse(name, args=[self.conversation_id, message_id, attachment_id])

    # --- images -----------------------------------------------------------

    def test_send_image_message(self):
        resp = self._post({"images": jpeg_upload()})
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        self.assertEqual(resp.data["message_type"], "image")

        attachments = resp.data["attachments"]
        self.assertEqual(len(attachments), 1)
        self.assertEqual(attachments[0]["kind"], "image")
        self.assertEqual(attachments[0]["status"], "ready")
        self.assertTrue(attachments[0]["poster_url"], "a thumbnail is always generated")
        self.assertGreater(attachments[0]["width"], 0)

    def test_image_is_downscaled_and_stripped(self):
        resp = self._post({"images": jpeg_upload(size=(4000, 3000))})
        attachment = MessageAttachment.objects.get(pk=resp.data["attachments"][0]["id"])

        # Nothing is stored at the original resolution.
        self.assertLessEqual(attachment.width, 900)
        with PILImage.open(attachment.file) as stored:
            self.assertIsNone(stored.getexif().get(0x8825), "GPS must not survive")
            self.assertEqual(stored.format, "JPEG")
        self.assertTrue(attachment.poster)
        self.assertGreater(attachment.size, 0)

    def test_several_images_keep_their_order(self):
        resp = self._post({"images": [jpeg_upload("a.jpg"), jpeg_upload("b.jpg"), jpeg_upload("c.jpg")]})
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        positions = list(
            MessageAttachment.objects.filter(message_id=resp.data["id"]).values_list("position", flat=True)
        )
        self.assertEqual(positions, [0, 1, 2])

    def test_rejects_a_file_that_is_not_an_image(self):
        fake = SimpleUploadedFile("evil.jpg", b"<html>not an image</html>", content_type="image/jpeg")
        resp = self._post({"images": fake})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(MessageAttachment.objects.count(), 0)

    def test_refuses_more_attachments_than_the_limit(self):
        with override_settings(MAX_ATTACHMENTS_PER_MESSAGE=2):
            resp = self._post({"images": [jpeg_upload("a.jpg"), jpeg_upload("b.jpg"), jpeg_upload("c.jpg")]})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(MessageAttachment.objects.count(), 0, "nothing is stored on refusal")

    # --- video ------------------------------------------------------------

    def test_send_video_with_poster(self):
        resp = self._post({"videos": video_upload(), "posters": jpeg_upload("poster.jpg"), "durations": 12})
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        self.assertEqual(resp.data["message_type"], "video")

        attachment = resp.data["attachments"][0]
        self.assertEqual(attachment["kind"], "video")
        self.assertEqual(attachment["duration"], 12)
        self.assertTrue(attachment["poster_url"], "the chat shows a still, not the video")

    def test_video_without_poster_still_sends(self):
        resp = self._post({"videos": video_upload(), "durations": 8})
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        self.assertIsNone(resp.data["attachments"][0]["poster_url"])

    def test_rejects_video_longer_than_the_limit(self):
        with override_settings(MAX_VIDEO_DURATION_SECONDS=30):
            resp = self._post({"videos": video_upload(), "durations": 120})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(MessageAttachment.objects.count(), 0)

    def test_rejects_a_file_that_is_not_a_video(self):
        fake = SimpleUploadedFile("evil.mp4", b"<html>not a video</html>", content_type="video/mp4")
        resp = self._post({"videos": fake, "durations": 5})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    # --- audio ------------------------------------------------------------

    def test_send_voice_message(self):
        resp = self._post({"audios": audio_upload(), "durations": 12})
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        self.assertEqual(resp.data["message_type"], "audio")
        self.assertEqual(resp.data["attachments"][0]["duration"], 12)

    def test_rejects_a_file_that_is_not_audio(self):
        fake = SimpleUploadedFile("evil.webm", b"<html>not audio</html>", content_type="audio/webm")
        resp = self._post({"audios": fake, "durations": 5})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rejects_audio_longer_than_the_limit(self):
        with override_settings(MAX_AUDIO_DURATION_SECONDS=60):
            resp = self._post({"audios": audio_upload(), "durations": 600})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    # --- mixed ------------------------------------------------------------

    def test_caption_travels_with_the_photo(self):
        resp = self._post({"images": jpeg_upload(), "body": "Voici l'article"})
        self.assertEqual(resp.data["body"], "Voici l'article")
        # Named after what it carries: the conversation list shows "Photo".
        self.assertEqual(resp.data["message_type"], "image")

    def test_empty_message_is_refused(self):
        resp = self._post({"body": ""})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_attachment_notifies_the_recipient(self):
        self._post({"images": jpeg_upload()})
        notification = Notification.objects.get(user=self.supplier_user)
        self.assertIn("Photo", notification.message)

    # --- access control ---------------------------------------------------

    def test_attachment_is_only_readable_by_participants(self):
        resp = self._post({"images": jpeg_upload()})
        url = self._attachment_url(resp.data["id"], resp.data["attachments"][0]["id"])

        self.client.force_authenticate(self.supplier_user)
        self.assertEqual(self.client.get(url).status_code, status.HTTP_200_OK)

        self.client.force_authenticate(self.outsider)
        self.assertEqual(self.client.get(url).status_code, status.HTTP_404_NOT_FOUND)

        self.client.force_authenticate(None)
        self.assertIn(
            self.client.get(url).status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    def test_poster_is_protected_like_the_file(self):
        resp = self._post({"images": jpeg_upload()})
        url = self._attachment_url(resp.data["id"], resp.data["attachments"][0]["id"], suffix="poster")

        self.client.force_authenticate(self.outsider)
        self.assertEqual(self.client.get(url).status_code, status.HTTP_404_NOT_FOUND)

    def test_attachment_of_another_conversation_is_not_reachable(self):
        """Changing the message id in the URL must not cross conversations."""
        resp = self._post({"images": jpeg_upload()})
        attachment_id = resp.data["attachments"][0]["id"]

        other_visitor = User.objects.create_user(phone="+22670050004", password="pw")
        self.client.force_authenticate(other_visitor)
        other_conversation = self.client.post(
            reverse("api:conversation-list"), {"product": self.product.pk}
        ).data["id"]

        url = reverse(
            "api:conversation-attachment",
            args=[other_conversation, resp.data["id"], attachment_id],
        )
        self.assertEqual(self.client.get(url).status_code, status.HTTP_404_NOT_FOUND)

    def test_media_is_streamed_never_redirected(self):
        resp = self._post({"images": jpeg_upload()})
        url = self._attachment_url(resp.data["id"], resp.data["attachments"][0]["id"])

        answer = self.client.get(url)
        self.assertEqual(answer.status_code, status.HTTP_200_OK)
        self.assertNotIn("Location", answer)
        self.assertEqual(answer["Content-Type"], "image/jpeg")
        self.assertIn("private", answer["Cache-Control"])

    def test_any_accept_header_is_served(self):
        resp = self._post({"images": jpeg_upload()})
        url = self._attachment_url(resp.data["id"], resp.data["attachments"][0]["id"])
        for accept in ("image/*", "*/*", "application/json"):
            with self.subTest(accept=accept):
                self.assertEqual(self.client.get(url, HTTP_ACCEPT=accept).status_code, 200)

    # --- storage layout ---------------------------------------------------

    def test_files_are_stored_under_the_conversation(self):
        resp = self._post({"images": jpeg_upload("../../etc/passwd.jpg")})
        attachment = MessageAttachment.objects.get(pk=resp.data["attachments"][0]["id"])
        expected = f"chat/{self.conversation_id}/{resp.data['id']}/"
        self.assertTrue(attachment.file.name.startswith(expected), attachment.file.name)
        # The name the user sent never reaches storage.
        self.assertNotIn("passwd", attachment.file.name)
        self.assertNotIn("..", attachment.file.name)

    def test_checksum_is_recorded(self):
        resp = self._post({"images": jpeg_upload()})
        attachment = MessageAttachment.objects.get(pk=resp.data["attachments"][0]["id"])
        self.assertEqual(len(attachment.checksum), 64)
