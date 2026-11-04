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
        self.staff = User.objects.create_user(phone="+22670030009", password="pw")
        self.staff.is_staff = True
        self.staff.save(update_fields=["is_staff"])
        self.profile = SupplierProfile.objects.get(user=self.supplier_user)
        self.product = Product.objects.create(
            supplier=self.profile, category=self.category, title="Tente",
            price=5000, city="Bobo", status=Product.Status.APPROVED,
        )

    def _start_conversation(self, user):
        self.client.force_authenticate(user)
        return self.client.post(reverse("api:conversation-list"), {"product": self.product.pk})

    def test_a_client_talks_to_nogoya_never_to_the_supplier(self):
        """Le virage du lancement : plus aucun fil ne vise un fournisseur.

        C'est ce qui permet de verifier une disponibilite avant d'annoncer
        quoi que ce soit, et de ne pas livrer un numero sans l'avoir decide.
        """
        resp = self._start_conversation(self.visitor)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        self.assertEqual(resp.data["other_participant"]["full_name"], "NOGOYA")
        self.assertNotEqual(resp.data["other_participant"]["id"], self.supplier_user.id)
        self.assertEqual(resp.data["audience"], Conversation.Audience.CLIENT)
        self.assertEqual(Conversation.objects.count(), 1)

        # Rouvrir le meme bien retrouve le fil, il n'en cree pas un second.
        resp2 = self._start_conversation(self.visitor)
        self.assertEqual(resp2.data["id"], resp.data["id"])
        self.assertEqual(Conversation.objects.count(), 1)

    def test_a_supplier_also_talks_to_nogoya(self):
        """Un fournisseur complete ses annonces avec l'equipe, pas avec un client."""
        resp = self._start_conversation(self.supplier_user)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        self.assertEqual(resp.data["audience"], Conversation.Audience.SUPPLIER)

    def test_a_member_has_exactly_one_thread_whatever_they_ask(self):
        """Un fil par annonce s'etait revele penible des deux cotes.

        Trois demandes donnaient trois conversations, et l'equipe suivait la
        meme personne dans plusieurs fils sans jamais voir l'ensemble. Le
        sujet est desormais porte par les messages, pas par le fil.
        """
        autre = Product.objects.create(
            supplier=self.profile, category=self.category, title="Chaises",
            price=1000, city="Bobo", status=Product.Status.APPROVED,
        )
        self.client.force_authenticate(self.visitor)
        a = self.client.post(reverse("api:conversation-list"), {"product": self.product.pk})
        b = self.client.post(reverse("api:conversation-list"), {"product": autre.pk})
        self.assertEqual(a.data["id"], b.data["id"])
        self.assertEqual(Conversation.objects.count(), 1)

    def test_the_team_sees_every_thread_and_answers_as_nogoya(self):
        conv_id = self._start_conversation(self.visitor).data["id"]

        self.client.force_authenticate(self.staff)
        listing = self.client.get(reverse("api:conversation-list"))
        self.assertEqual(listing.data["count"], 1)
        # L'equipe, elle, a besoin de savoir a qui elle parle.
        self.assertEqual(
            listing.data["results"][0]["other_participant"]["id"], self.visitor.id
        )

        send = self.client.post(
            reverse("api:conversation-messages", args=[conv_id]), {"body": "Nous verifions."}
        )
        self.assertEqual(send.status_code, status.HTTP_201_CREATED, send.data)

        # Le client voit « NOGOYA », pas le nom de la personne de permanence.
        from .models import Message
        message = Message.objects.get(pk=send.data["id"])
        self.assertEqual(message.sender.public_name(), "NOGOYA")
        self.assertEqual(message.staff_author, self.staff)

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

        self.client.force_authenticate(self.staff)
        listing = self.client.get(reverse("api:conversation-messages", args=[conv_id]))
        self.assertEqual(listing.data["results"][0]["body"], "Bonjour, encore dispo ?")
        self.assertFalse(listing.data["results"][0]["is_mine"])

        unread = self.client.get(reverse("api:conversation-unread-count"))
        self.assertEqual(unread.data["unread_count"], 1)

        self.client.post(reverse("api:conversation-read", args=[conv_id]))
        unread_after = self.client.get(reverse("api:conversation-unread-count"))
        self.assertEqual(unread_after.data["unread_count"], 0)

    def test_each_side_sees_its_own_messages_as_its_own(self):
        """Les reponses de l'equipe partent au nom de NOGOYA.

        Comparer au seul `request.user` rendait donc TOUS les messages
        « pas de moi » cote equipe — ses propres reponses comme celles du
        membre — et la conversation s'affichait d'une seule couleur, alors
        que cote membre la meme conversation paraissait normale.
        """
        conv_id = self._start_conversation(self.visitor).data["id"]
        self.client.post(
            reverse("api:conversation-messages", args=[conv_id]), {"body": "Bonjour"}
        )
        self.client.force_authenticate(self.staff)
        self.client.post(
            reverse("api:conversation-messages", args=[conv_id]), {"body": "Nous verifions."}
        )

        vu_par_equipe = {
            m["body"]: m["is_mine"]
            for m in self.client.get(
                reverse("api:conversation-messages", args=[conv_id])
            ).data["results"]
        }
        self.assertFalse(vu_par_equipe["Bonjour"])
        self.assertTrue(vu_par_equipe["Nous verifions."])

        self.client.force_authenticate(self.visitor)
        vu_par_membre = {
            m["body"]: m["is_mine"]
            for m in self.client.get(
                reverse("api:conversation-messages", args=[conv_id])
            ).data["results"]
        }
        self.assertTrue(vu_par_membre["Bonjour"])
        self.assertFalse(vu_par_membre["Nous verifions."])

    def test_the_team_does_not_count_its_own_answers_as_unread(self):
        """Le meme travers que la couleur des bulles, dans la liste des fils.

        L'equipe repond au nom de NOGOYA : exclure `request.user` du
        compteur n'excluait donc rien. Chaque reponse qu'elle venait
        d'ecrire faisait remonter le fil en tete avec une pastille rouge,
        et l'apercu perdait son « Vous : » — comme si le membre avait
        repondu a sa place.
        """
        conv_id = self._start_conversation(self.visitor).data["id"]
        self.client.post(
            reverse("api:conversation-messages", args=[conv_id]), {"body": "Bonjour"}
        )

        self.client.force_authenticate(self.staff)
        # L'equipe ouvre le fil, puis repond.
        self.client.post(reverse("api:conversation-read", args=[conv_id]))
        self.client.post(
            reverse("api:conversation-messages", args=[conv_id]), {"body": "Nous verifions."}
        )

        fil = self.client.get(reverse("api:conversation-list")).data["results"][0]
        self.assertEqual(fil["unread_count"], 0)
        self.assertEqual(fil["last_message"]["body"], "Nous verifions.")
        self.assertTrue(fil["last_message"]["is_mine"])

        # Et cote membre, la meme reponse est bien un message non lu.
        self.client.force_authenticate(self.visitor)
        fil_membre = self.client.get(reverse("api:conversation-list")).data["results"][0]
        self.assertEqual(fil_membre["unread_count"], 1)
        self.assertFalse(fil_membre["last_message"]["is_mine"])

    def test_an_anonymous_reader_owns_nothing(self):
        conv_id = self._start_conversation(self.visitor).data["id"]
        self.client.post(
            reverse("api:conversation-messages", args=[conv_id]), {"body": "Bonjour"}
        )
        self.client.force_authenticate(None)
        resp = self.client.get(reverse("api:conversation-messages", args=[conv_id]))
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_a_system_note_belongs_to_nobody(self):
        """Le recapitulatif d'une demande n'est pas un message du client.

        L'attribuer le faisait passer pour quelque chose qu'il aurait
        ecrit, des deux cotes de la conversation.
        """
        from .models import Message

        conv_id = self._start_conversation(self.visitor).data["id"]
        Message.objects.create(
            conversation_id=conv_id, sender=self.visitor,
            message_type=Message.Type.SYSTEM, body="Demande de location",
        )

        for lecteur in (self.visitor, self.staff):
            with self.subTest(lecteur=lecteur.phone):
                self.client.force_authenticate(lecteur)
                note = next(
                    m for m in self.client.get(
                        reverse("api:conversation-messages", args=[conv_id])
                    ).data["results"]
                    if m["message_type"] == "system"
                )
                self.assertFalse(note["is_mine"])

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

        self.client.force_authenticate(self.staff)
        resp = self.client.post(reverse("api:message-report-list"), {"message": msg_id, "reason": "spam"})
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

        outsider = User.objects.create_user(phone="+22670030099", password="pw")
        self.client.force_authenticate(outsider)
        resp2 = self.client.post(reverse("api:message-report-list"), {"message": msg_id, "reason": "x"})
        self.assertEqual(resp2.status_code, status.HTTP_404_NOT_FOUND)
