"""La mise en relation doit réellement mettre en relation.

Elle passait la demande à « mise en relation faite » sans rien envoyer : le
client n'avait aucun moyen de joindre le fournisseur, et l'équipe ne voyait
pas le numéro pour le lui relayer.
"""
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.catalog.models import Category, Product
from apps.messaging.models import Message
from apps.messaging.services import support_account
from apps.notifications.models import Notification

from .models import RentalRequest

User = get_user_model()


class ContactReleaseTests(APITestCase):
    def setUp(self):
        category = Category.objects.create(name="Logements")
        self.supplier = User.objects.create_user(
            phone="+22670060001", password="pw", role=User.Role.SUPPLIER,
            first_name="Issa", last_name="Ouédraogo",
        )
        profile = self.supplier.supplier_profile
        profile.whatsapp_number = "+22676060001"
        profile.allow_whatsapp_contact = True
        profile.save()

        self.client_user = User.objects.create_user(phone="+22670060002", password="pw")
        self.staff = User.objects.create_user(phone="+22670060009", password="pw")
        self.staff.is_staff = True
        self.staff.save(update_fields=["is_staff"])

        self.product = Product.objects.create(
            supplier=profile, category=category, title="Villa 3 chambres",
            price=250000, city="Ouagadougou",
            status=Product.Status.APPROVED, is_active=True,
        )
        self.start = date.today() + timedelta(days=7)

    def _request(self, user=None, **extra):
        if user is not None:
            self.client.force_authenticate(user)
        else:
            self.client.force_authenticate(None)
        payload = {
            "product": self.product.pk,
            "start_date": self.start.isoformat(),
            "end_date": (self.start + timedelta(days=3)).isoformat(),
            "message": "Libre ?",
            **extra,
        }
        resp = self.client.post(reverse("api:rental-request-list"), payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        return RentalRequest.objects.get(pk=resp.data["id"])

    def _release(self, demande):
        self.client.force_authenticate(self.staff)
        self.client.post(reverse("api:rental-request-available", args=[demande.pk]))
        return self.client.post(reverse("api:rental-request-release-contact", args=[demande.pk]))

    # --- le message au client ------------------------------------------

    def test_the_client_receives_the_supplier_contact_in_the_thread(self):
        demande = self._request(self.client_user)
        resp = self._release(demande)
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)

        message = Message.objects.filter(conversation=demande.thread).latest("created_at")
        self.assertEqual(message.sender, support_account())
        self.assertIn("+22670060001", message.body)
        self.assertIn("+22676060001", message.body)
        self.assertIn("Issa Ouédraogo", message.body)
        self.assertEqual(message.shared_product, self.product)
        # Il doit compter comme non lu : c'est ce qui allume la pastille.
        self.assertIsNone(message.read_at)

    def test_the_client_sees_it_as_coming_from_nogoya(self):
        demande = self._request(self.client_user)
        self._release(demande)

        self.client.force_authenticate(self.client_user)
        messages = self.client.get(
            reverse("api:conversation-messages", args=[demande.thread_id])
        ).data["results"]
        contact = next(m for m in messages if "+22670060001" in m["body"])
        self.assertFalse(contact["is_mine"])

        # Et l'équipe, dans le même fil, le voit comme sa propre réponse.
        self.client.force_authenticate(self.staff)
        messages = self.client.get(
            reverse("api:conversation-messages", args=[demande.thread_id])
        ).data["results"]
        contact = next(m for m in messages if "+22670060001" in m["body"])
        self.assertTrue(contact["is_mine"])

    def test_the_client_is_notified(self):
        demande = self._request(self.client_user)
        self._release(demande)
        notification = Notification.objects.get(user=self.client_user)
        self.assertEqual(notification.type, Notification.Type.NEW_MESSAGE)
        self.assertIn(str(demande.thread_id), notification.url)

    def test_releasing_twice_sends_the_contact_once(self):
        """Un double clic, ou deux personnes de l'équipe sur la même demande."""
        demande = self._request(self.client_user)
        self._release(demande)
        self.client.post(reverse("api:rental-request-release-contact", args=[demande.pk]))

        envoyes = Message.objects.filter(
            conversation=demande.thread, body__contains="+22670060001"
        )
        self.assertEqual(envoyes.count(), 1)
        self.assertEqual(Notification.objects.filter(user=self.client_user).count(), 1)

    def test_whatsapp_is_withheld_when_the_supplier_has_not_allowed_it(self):
        profile = self.supplier.supplier_profile
        profile.allow_whatsapp_contact = False
        profile.save()
        demande = self._request(self.client_user)
        self._release(demande)

        message = Message.objects.filter(conversation=demande.thread).latest("created_at")
        self.assertIn("+22670060001", message.body)
        self.assertNotIn("+22676060001", message.body)

    # --- ce que chacun lit sur la demande --------------------------------

    def test_the_client_cannot_read_the_contact_before_release(self):
        """Tout le principe du schéma, tenu par le serveur."""
        demande = self._request(self.client_user)
        self.client.force_authenticate(self.client_user)
        lu = self.client.get(reverse("api:rental-request-detail", args=[demande.pk])).data
        self.assertIsNone(lu["supplier_contact"])
        self.assertNotIn("supplier_phone", lu)

    def test_the_client_finds_the_contact_on_the_request_after_release(self):
        """Même si le message du fil s'est perdu, la demande le porte."""
        demande = self._request(self.client_user)
        self._release(demande)
        self.client.force_authenticate(self.client_user)
        lu = self.client.get(reverse("api:rental-request-detail", args=[demande.pk])).data
        self.assertEqual(lu["supplier_contact"]["phone"], "+22670060001")
        self.assertEqual(lu["supplier_contact"]["whatsapp"], "+22676060001")

    def test_the_team_sees_the_supplier_number_to_check_availability(self):
        """Avant la mise en relation : c'est l'équipe qui appelle."""
        demande = self._request(self.client_user)
        self.client.force_authenticate(self.staff)
        lu = self.client.get(reverse("api:rental-request-detail", args=[demande.pk])).data
        self.assertEqual(lu["supplier_phone"], "+22670060001")
        self.assertEqual(lu["supplier_whatsapp"], "+22676060001")

    # --- le visiteur sans compte -----------------------------------------

    def test_a_guest_release_writes_nothing_but_the_team_has_both_numbers(self):
        """Pas de fil, donc pas de message : l'équipe appelle, et doit pouvoir."""
        demande = self._request(guest_name="Awa", guest_phone="70 11 22 33")
        self.assertIsNone(demande.thread_id)

        resp = self._release(demande)
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        # Le numero du visiteur est garde tel que saisi, espaces retires.
        self.assertEqual(resp.data["requester_phone"], "70112233")
        self.assertEqual(resp.data["supplier_phone"], "+22670060001")
        self.assertEqual(Notification.objects.count(), 0)
