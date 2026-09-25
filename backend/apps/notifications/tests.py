from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Notification
from .services import notify, unread_count_for

User = get_user_model()


class NotificationApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(phone="+22670060001", password="pw")
        self.other = User.objects.create_user(phone="+22670060002", password="pw")
        notify(self.user, type=Notification.Type.SYSTEM, title="Bienvenue", message="Hello")
        notify(self.user, type=Notification.Type.NEW_PRODUCT, title="Nouvelle annonce", url="/produits/x")
        notify(self.other, type=Notification.Type.SYSTEM, title="Pas pour vous")

    def test_list_is_scoped_to_the_requester(self):
        self.client.force_authenticate(self.user)
        resp = self.client.get(reverse("api:notification-list"))
        self.assertEqual(resp.data["count"], 2)
        titles = {n["title"] for n in resp.data["results"]}
        self.assertNotIn("Pas pour vous", titles)

    def test_requires_authentication(self):
        resp = self.client.get(reverse("api:notification-list"))
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unread_count_and_mark_one_read(self):
        self.client.force_authenticate(self.user)
        self.assertEqual(
            self.client.get(reverse("api:notification-unread-count")).data["unread_count"], 2
        )

        first = Notification.objects.filter(user=self.user).first()
        read = self.client.post(reverse("api:notification-read", args=[first.pk]))
        self.assertEqual(read.status_code, status.HTTP_200_OK)
        self.assertTrue(read.data["is_read"])
        self.assertEqual(unread_count_for(self.user), 1)

    def test_mark_all_read(self):
        self.client.force_authenticate(self.user)
        resp = self.client.post(reverse("api:notification-read-all"))
        self.assertEqual(resp.data["marked_read"], 2)
        self.assertEqual(unread_count_for(self.user), 0)
        # the other user's notification is untouched
        self.assertEqual(unread_count_for(self.other), 1)

    def test_cannot_mark_someone_elses_notification_read(self):
        theirs = Notification.objects.get(user=self.other)
        self.client.force_authenticate(self.user)
        resp = self.client.post(reverse("api:notification-read", args=[theirs.pk]))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        theirs.refresh_from_db()
        self.assertIsNone(theirs.read_at)

    def test_unread_filter(self):
        self.client.force_authenticate(self.user)
        first = Notification.objects.filter(user=self.user).first()
        self.client.post(reverse("api:notification-read", args=[first.pk]))
        resp = self.client.get(reverse("api:notification-list") + "?unread=true")
        self.assertEqual(resp.data["count"], 1)
