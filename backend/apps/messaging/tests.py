from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.catalog.models import Category, Product
from apps.suppliers.models import SupplierProfile

from .models import Conversation

User = get_user_model()


class MessagingApiTests(APITestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Tentes")
        self.supplier_user = User.objects.create_user(
            phone="+22670030001", password="pw", role=User.Role.SUPPLIER
        )
        self.other_supplier_user = User.objects.create_user(
            phone="+22670030002", password="pw", role=User.Role.SUPPLIER
        )
        self.visitor = User.objects.create_user(
            phone="+22670030003", password="pw", role=User.Role.VISITOR
        )
        self.profile = SupplierProfile.objects.get(user=self.supplier_user)
        self.product = Product.objects.create(
            supplier=self.profile, category=self.category, title="Tente",
            price=5000, city="Bobo", status=Product.Status.APPROVED,
        )

    def _start_conversation(self, user):
        self.client.force_authenticate(user)
        return self.client.post(reverse("api:conversation-list"), {"product": self.product.pk})

    def test_visitor_starts_conversation_with_supplier(self):
        resp = self._start_conversation(self.visitor)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        self.assertEqual(resp.data["other_participant"]["id"], self.supplier_user.id)
        self.assertEqual(Conversation.objects.count(), 1)

        # starting again returns the same conversation, not a duplicate
        resp2 = self._start_conversation(self.visitor)
        self.assertEqual(resp2.data["id"], resp.data["id"])
        self.assertEqual(Conversation.objects.count(), 1)

    def test_supplier_cannot_start_conversation_with_self(self):
        resp = self._start_conversation(self.supplier_user)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_non_participant_cannot_access_conversation(self):
        conv_id = self._start_conversation(self.visitor).data["id"]
        self.client.force_authenticate(self.other_supplier_user)
        resp = self.client.get(reverse("api:conversation-detail", args=[conv_id]))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_send_and_list_messages_with_unread_tracking(self):
        conv_id = self._start_conversation(self.visitor).data["id"]

        send = self.client.post(
            reverse("api:conversation-messages", args=[conv_id]), {"body": "Bonjour, encore dispo ?"}
        )
        self.assertEqual(send.status_code, status.HTTP_201_CREATED, send.data)

        self.client.force_authenticate(self.supplier_user)
        listing = self.client.get(reverse("api:conversation-messages", args=[conv_id]))
        self.assertEqual(listing.data["results"][0]["body"], "Bonjour, encore dispo ?")
        self.assertFalse(listing.data["results"][0]["is_mine"])

        unread = self.client.get(reverse("api:conversation-unread-count"))
        self.assertEqual(unread.data["unread_count"], 1)

        self.client.post(reverse("api:conversation-read", args=[conv_id]))
        unread_after = self.client.get(reverse("api:conversation-unread-count"))
        self.assertEqual(unread_after.data["unread_count"], 0)

    def test_message_requires_body_or_product(self):
        conv_id = self._start_conversation(self.visitor).data["id"]
        resp = self.client.post(reverse("api:conversation-messages", args=[conv_id]), {})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_sharing_a_product_in_a_message(self):
        conv_id = self._start_conversation(self.visitor).data["id"]
        other_product = Product.objects.create(
            supplier=self.profile, category=self.category, title="Chaises",
            price=1000, city="Bobo", status=Product.Status.APPROVED,
        )
        resp = self.client.post(
            reverse("api:conversation-messages", args=[conv_id]),
            {"body": "", "shared_product": other_product.pk},
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        self.assertEqual(resp.data["shared_product"]["id"], other_product.pk)

    def test_block_prevents_further_messages(self):
        conv_id = self._start_conversation(self.visitor).data["id"]
        self.client.post(reverse("api:conversation-block", args=[conv_id]))
        resp = self.client.post(reverse("api:conversation-messages", args=[conv_id]), {"body": "Hé ?"})
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_report_message(self):
        conv_id = self._start_conversation(self.visitor).data["id"]
        msg_id = self.client.post(
            reverse("api:conversation-messages", args=[conv_id]), {"body": "spam"}
        ).data["id"]

        self.client.force_authenticate(self.supplier_user)
        resp = self.client.post(reverse("api:message-report-list"), {"message": msg_id, "reason": "spam"})
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

        outsider = User.objects.create_user(phone="+22670030099", password="pw")
        self.client.force_authenticate(outsider)
        resp2 = self.client.post(reverse("api:message-report-list"), {"message": msg_id, "reason": "x"})
        self.assertEqual(resp2.status_code, status.HTTP_404_NOT_FOUND)
