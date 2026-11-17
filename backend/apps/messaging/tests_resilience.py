"""Un envoi enregistré ne doit jamais répondre par une erreur.

Mesuré en production le 2026-11-17 : quand l'équipe envoyait une photo ou un
vocal, le message s'enregistrait, puis la notification du membre, qui
commençait par un emoji, était refusée par une base dont les tables ne sont
pas en utf8mb4. Le serveur répondait 500, et l'équipe voyait « L'envoi a
échoué » sur un message pourtant parti, qu'elle risquait de renvoyer.
"""
import io
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import OperationalError
from django.urls import reverse
from PIL import Image as PILImage
from rest_framework import status
from rest_framework.test import APITestCase

from apps.catalog.models import Category, Product
from apps.core.errors import is_unsupported_character
from apps.notifications.models import Notification

from .models import Message

User = get_user_model()


def photo():
    buf = io.BytesIO()
    PILImage.new("RGB", (64, 48), (200, 100, 50)).save(buf, format="JPEG")
    return SimpleUploadedFile("photo.jpg", buf.getvalue(), content_type="image/jpeg")


class SendResilienceTests(APITestCase):
    def setUp(self):
        category = Category.objects.create(name="Tentes")
        supplier = User.objects.create_user(
            phone="+22670080001", password="pw", role=User.Role.SUPPLIER
        )
        self.product = Product.objects.create(
            supplier=supplier.supplier_profile, category=category, title="Tente",
            price=5000, city="Bobo", status=Product.Status.APPROVED,
        )
        self.member = User.objects.create_user(phone="+22670080002", password="pw")
        self.staff = User.objects.create_user(phone="+22670080009", password="pw")
        self.staff.is_staff = True
        self.staff.save(update_fields=["is_staff"])

        self.client.force_authenticate(self.member)
        self.thread = self.client.post(
            reverse("api:conversation-list"), {"product": self.product.pk}
        ).data["id"]
        self.url = reverse("api:conversation-messages", args=[self.thread])

    def test_a_failing_notification_does_not_turn_a_sent_photo_into_an_error(self):
        self.client.force_authenticate(self.staff)
        with patch(
            "apps.messaging.api.notify",
            side_effect=OperationalError(1366, "Incorrect string value: '\\xF0\\x9F...'"),
        ):
            resp = self.client.post(self.url, {"images": [photo()]}, format="multipart")

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        self.assertEqual(resp.data["message_type"], "image")
        self.assertEqual(Message.objects.filter(conversation_id=self.thread).count(), 1)

    def test_the_team_s_photo_notification_carries_no_emoji(self):
        """Écrite en base : elle doit passer même sur des tables en utf8 3 octets."""
        self.client.force_authenticate(self.staff)
        self.client.post(self.url, {"images": [photo()]}, format="multipart")

        notification = Notification.objects.get(user=self.member)
        self.assertEqual(notification.message, "Photo")
        self.assertTrue(
            all(ord(ch) <= 0xFFFF for ch in notification.title + notification.message),
            "un caractère hors du plan de base, refusé par utf8 3 octets",
        )

    def test_an_unstorable_character_gets_a_clear_message(self):
        """Pas « le serveur n'a pas pu enregistrer ce fichier » pour un texte."""
        self.client.force_authenticate(self.member)
        with patch(
            "apps.messaging.api.build_attachments",
            side_effect=OperationalError(1366, "Incorrect string value: '\\xF0\\x9F\\x98\\x80'"),
        ):
            resp = self.client.post(self.url, {"body": "Bonjour"}, format="json")

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, resp.data)
        self.assertIn("emoji", resp.data["detail"])
        self.assertNotIn("fichier", resp.data["detail"])
        # La transaction est défaite : rien de partiel ne reste.
        self.assertEqual(Message.objects.filter(conversation_id=self.thread).count(), 0)


class UnsupportedCharacterDetectionTests(APITestCase):
    def test_recognises_the_mysql_error(self):
        self.assertTrue(is_unsupported_character(OperationalError(1366, "Incorrect string value")))
        self.assertTrue(
            is_unsupported_character(Exception("(1366, \"Incorrect string value: '\\xF0'\")"))
        )

    def test_does_not_mistake_other_failures(self):
        self.assertFalse(is_unsupported_character(OperationalError(2006, "MySQL server has gone away")))
        self.assertFalse(is_unsupported_character(OSError(28, "No space left on device")))
