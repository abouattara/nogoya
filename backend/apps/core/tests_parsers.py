"""Le corps multipart encapsulé est bien reçu — et rien d'autre ne l'est.

Ces tests reproduisent exactement ce que fabrique `frontend/src/lib/
multipart.ts` : un corps multipart standard, étiqueté
`application/octet-stream`, avec la frontière dans un en-tête.
"""
import io
import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from PIL import Image as PILImage
from rest_framework import status
from rest_framework.test import APITestCase

from apps.catalog.models import Category, Product

User = get_user_model()
MEDIA = tempfile.mkdtemp(prefix="nogoya_parser_media_")
BOUNDARY = "nogoya0123456789abcdef"


def jpeg_bytes(size=(800, 600)):
    buffer = io.BytesIO()
    PILImage.new("RGB", size, (30, 140, 90)).save(buffer, format="JPEG", quality=90)
    return buffer.getvalue()


def encode_multipart(parts, boundary=BOUNDARY):
    """Mêmes octets que le navigateur produirait pour ce FormData.

    `parts` : liste de (nom, valeur) où la valeur est soit une chaîne, soit
    un triplet (nom_de_fichier, octets, type_mime).
    """
    body = b""
    for name, value in parts:
        body += f"--{boundary}\r\n".encode()
        if isinstance(value, str):
            body += f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode()
            body += value.encode()
        else:
            filename, content, content_type = value
            body += (
                f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'
                f"Content-Type: {content_type}\r\n\r\n"
            ).encode()
            body += content
        body += b"\r\n"
    return body + f"--{boundary}--\r\n".encode()


@override_settings(MEDIA_ROOT=MEDIA, CELERY_TASK_ALWAYS_EAGER=True)
class WrappedMultiPartParserTests(APITestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(MEDIA, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.category = Category.objects.create(name="Tentes")
        self.user = User.objects.create_user(
            phone="+22670070001", password="pw", role=User.Role.SUPPLIER
        )
        # Le profil fournisseur est créé par un signal à l'inscription.
        self.profile = self.user.supplier_profile
        self.product = Product.objects.create(
            supplier=self.profile, category=self.category,
            title="Tente", price=5000, city="Ouaga",
        )
        self.url = reverse("api:product-upload-images", args=[self.product.slug])
        self.client.force_authenticate(self.user)

    def _post(self, body, boundary=BOUNDARY, header=True):
        extra = {"HTTP_X_UPLOAD_BOUNDARY": boundary} if header else {}
        return self.client.post(
            self.url, data=body, content_type="application/octet-stream", **extra
        )

    def test_encapsulated_body_uploads_the_image(self):
        body = encode_multipart([("images", ("photo.jpg", jpeg_bytes(), "image/jpeg"))])
        resp = self._post(body)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        self.assertEqual(self.product.images.count(), 1)

    def test_several_files_and_text_fields_in_one_body(self):
        body = encode_multipart([
            ("images", ("a.jpg", jpeg_bytes(), "image/jpeg")),
            ("images", ("b.jpg", jpeg_bytes((400, 300)), "image/jpeg")),
        ])
        resp = self._post(body)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        self.assertEqual(self.product.images.count(), 2)

    def test_missing_boundary_header_is_refused(self):
        body = encode_multipart([("images", ("photo.jpg", jpeg_bytes(), "image/jpeg"))])
        resp = self._post(body, header=False)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.product.images.count(), 0)

    def test_boundary_from_the_client_is_never_trusted(self):
        # Un point-virgule ou un guillemet dans la frontière permettrait de
        # fabriquer des paramètres d'en-tête supplémentaires côté serveur.
        body = encode_multipart([("images", ("photo.jpg", jpeg_bytes(), "image/jpeg"))])
        for hostile in ('x"; name=y', "short", "a;b=c", "../../etc"):
            with self.subTest(boundary=hostile):
                resp = self._post(body, boundary=hostile)
                self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.product.images.count(), 0)

    def test_plain_multipart_still_works(self):
        """La voie normale reste ouverte : admin Django, tests, autre hébergeur."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        resp = self.client.post(
            self.url,
            {"images": SimpleUploadedFile("photo.jpg", jpeg_bytes(), content_type="image/jpeg")},
            format="multipart",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        self.assertEqual(self.product.images.count(), 1)

    def test_validation_still_applies_to_an_encapsulated_file(self):
        """L'encapsulation change l'étiquette, pas les contrôles."""
        body = encode_multipart([("images", ("fake.jpg", b"<html>pas une image</html>", "image/jpeg"))])
        resp = self._post(body)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.product.images.count(), 0)
