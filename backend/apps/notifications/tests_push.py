from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import DeviceToken, Notification
from .services import notify

User = get_user_model()


class DeviceRegistrationTests(APITestCase):
    def setUp(self):
        self.awa = User.objects.create_user(phone="+22670050001", password="pw")
        self.issa = User.objects.create_user(phone="+22670050002", password="pw")

    def test_an_app_registers_its_device(self):
        self.client.force_authenticate(self.awa)
        resp = self.client.post(
            reverse("api:device-list"),
            {"token": "jeton-abc", "platform": "android"},
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        self.assertTrue(DeviceToken.objects.filter(user=self.awa, token="jeton-abc").exists())

    def test_registering_twice_keeps_one_device(self):
        """Relancer l'application ne doit pas multiplier les lignes."""
        self.client.force_authenticate(self.awa)
        for attempt in range(3):
            resp = self.client.post(reverse("api:device-list"), {"token": "jeton-abc"})
            # Chaque appel doit réussir : un 400 au deuxième lancement
            # ferait croire à l'application qu'elle n'est pas inscrite.
            self.assertEqual(
                resp.status_code, status.HTTP_201_CREATED, f"essai {attempt}: {resp.data}"
            )
        self.assertEqual(DeviceToken.objects.filter(token="jeton-abc").count(), 1)

    def test_a_second_account_on_the_same_phone_takes_the_device_over(self):
        """Deux comptes, un seul téléphone.

        Le jeton désigne l'installation, pas la personne. Le laisser
        attaché au premier compte enverrait les notifications d'Awa sur
        l'écran d'Issa.
        """
        self.client.force_authenticate(self.awa)
        self.client.post(reverse("api:device-list"), {"token": "jeton-partage"})

        self.client.force_authenticate(self.issa)
        resp = self.client.post(reverse("api:device-list"), {"token": "jeton-partage"})
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)

        self.assertEqual(DeviceToken.objects.filter(token="jeton-partage").count(), 1)
        self.assertEqual(
            DeviceToken.objects.get(token="jeton-partage").user_id, self.issa.id
        )

    def test_nobody_can_silence_someone_else_s_device(self):
        """Connaître un jeton ne doit pas suffire à le supprimer."""
        DeviceToken.objects.create(user=self.awa, token="jeton-awa")

        self.client.force_authenticate(self.issa)
        resp = self.client.delete(reverse("api:device-detail", args=["jeton-awa"]))

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(DeviceToken.objects.filter(token="jeton-awa").exists())

    def test_its_owner_can_remove_it(self):
        DeviceToken.objects.create(user=self.awa, token="jeton-awa")
        self.client.force_authenticate(self.awa)
        resp = self.client.delete(reverse("api:device-detail", args=["jeton-awa"]))
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(DeviceToken.objects.filter(token="jeton-awa").exists())

    def test_registering_requires_an_account(self):
        resp = self.client.post(reverse("api:device-list"), {"token": "jeton-anonyme"})
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(DeviceToken.objects.count(), 0)


class PushDeliveryTests(APITestCase):
    def setUp(self):
        self.awa = User.objects.create_user(phone="+22670050003", password="pw")

    @override_settings(FCM_CREDENTIALS_FILE="", FCM_PROJECT_ID="")
    def test_everything_works_without_firebase(self):
        """Sans Firebase, la notification existe quand même.

        C'est la notification en base que le site et l'application
        lisent ; le push n'est qu'une alerte pour l'application fermée.
        Faire dépendre l'une de l'autre casserait le service le jour où
        la clé expire.
        """
        notification = notify(
            self.awa, type=Notification.Type.NEW_MESSAGE, title="Un message"
        )
        self.assertIsNotNone(notification)
        self.assertEqual(Notification.objects.filter(user=self.awa).count(), 1)

    def test_a_push_failure_never_breaks_what_triggered_it(self):
        """Un envoi qui lève ne doit pas faire échouer l'envoi du message."""
        with patch(
            "apps.notifications.services.send_to_user",
            side_effect=RuntimeError("Firebase est tombé"),
        ):
            notification = notify(
                self.awa, type=Notification.Type.NEW_MESSAGE, title="Un message"
            )
        self.assertIsNotNone(notification)
        self.assertEqual(Notification.objects.filter(user=self.awa).count(), 1)

    def test_a_rejected_token_is_forgotten(self):
        """Une application désinstallée ne doit pas encombrer la table."""
        DeviceToken.objects.create(user=self.awa, token="jeton-mort")
        from .push import send_to_user

        with patch(
            "apps.notifications.push.send_to_tokens", return_value=["jeton-mort"]
        ):
            send_to_user(self.awa, title="Un message", body="Bonjour")

        self.assertFalse(DeviceToken.objects.filter(token="jeton-mort").exists())

    @override_settings(FCM_CREDENTIALS_FILE="", FCM_PROJECT_ID="")
    def test_nothing_is_sent_when_there_is_no_device(self):
        from .push import send_to_tokens

        self.assertEqual(send_to_tokens([], title="t", body="b"), [])
