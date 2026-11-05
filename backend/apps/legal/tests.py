from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import TermsAcceptance
from .terms import TERMS_VERSION

User = get_user_model()


def inscription(**overrides):
    payload = {
        "phone": "+22670040001",
        "first_name": "Awa",
        "last_name": "Traoré",
        "role": "visitor",
        "password": "UnMotDePasseSolide9",
        "password2": "UnMotDePasseSolide9",
        "accept_terms": True,
    }
    payload.update(overrides)
    return payload


class TermsAcceptanceTests(APITestCase):
    """Accepter les conditions est une condition d'inscription, pas un décor."""

    def test_an_acceptance_is_recorded_with_the_version_shown(self):
        """Une trace sans version ne vaut rien six mois plus tard."""
        resp = self.client.post(reverse("api:auth-register"), inscription())
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)

        user = User.objects.get(phone="+22670040001")
        acceptation = TermsAcceptance.objects.get(user=user)
        self.assertEqual(acceptation.version, TERMS_VERSION)
        self.assertIsNotNone(acceptation.accepted_at)
        self.assertTrue(TermsAcceptance.is_up_to_date(user))

    def test_registration_without_acceptance_is_refused(self):
        """La case décochée dans le navigateur ne prouve rien.

        Elle se recoche depuis la console, et l'appel part quand même.
        C'est donc le serveur qui refuse, et aucun compte ne naît.
        """
        # En JSON, comme le navigateur : `None` ne s'encode pas en
        # multipart, et c'est précisément une des formes que prend un
        # appel bricolé à la main.
        for valeur in (False, None, "", 0):
            with self.subTest(accept_terms=valeur):
                resp = self.client.post(
                    reverse("api:auth-register"),
                    inscription(accept_terms=valeur),
                    format="json",
                )
                self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, resp.data)
                self.assertIn("accept_terms", resp.data)
                self.assertFalse(User.objects.filter(phone="+22670040001").exists())

    def test_the_field_cannot_simply_be_left_out(self):
        """Omettre le champ serait le moyen le plus simple de le contourner."""
        payload = inscription()
        payload.pop("accept_terms")
        resp = self.client.post(reverse("api:auth-register"), payload)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, resp.data)
        self.assertFalse(User.objects.filter(phone="+22670040001").exists())

    def test_an_outdated_version_is_refused_with_what_to_do(self):
        """Un onglet resté ouvert pendant une mise à jour du texte.

        Enregistrer cet accord reviendrait à dire que la personne a
        accepté un texte qui ne s'applique plus.
        """
        resp = self.client.post(
            reverse("api:auth-register"), inscription(terms_version="2020-01-01")
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, resp.data)
        self.assertIn("Rechargez la page", " ".join(resp.data["terms_version"]))
        self.assertFalse(User.objects.filter(phone="+22670040001").exists())

    def test_the_version_in_use_is_accepted(self):
        resp = self.client.post(
            reverse("api:auth-register"), inscription(terms_version=TERMS_VERSION)
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)

    def test_a_refused_registration_leaves_no_trace_at_all(self):
        """Ni compte orphelin, ni acceptation orpheline."""
        self.client.post(reverse("api:auth-register"), inscription(password2="autre"))
        self.assertFalse(User.objects.filter(phone="+22670040001").exists())
        self.assertEqual(TermsAcceptance.objects.count(), 0)

    def test_recording_twice_does_not_duplicate(self):
        """Deux acceptations de la même version restent une seule ligne."""
        user = User.objects.create_user(phone="+22670040009", password="pw")
        TermsAcceptance.record(user)
        TermsAcceptance.record(user)
        self.assertEqual(TermsAcceptance.objects.filter(user=user).count(), 1)

    def test_a_new_version_is_not_considered_accepted(self):
        """Changer le texte redemande l'accord, sans effacer le précédent."""
        user = User.objects.create_user(phone="+22670040010", password="pw")
        TermsAcceptance.record(user, version="2020-01-01")
        self.assertFalse(TermsAcceptance.is_up_to_date(user))
        self.assertTrue(
            TermsAcceptance.objects.filter(user=user, version="2020-01-01").exists()
        )
