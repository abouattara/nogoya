"""Recevoir des fichiers quand l'hébergeur refuse les formulaires multipart.

Sur l'hébergement mutualisé (LiteSpeed + ModSecurity), *toute* requête dont
le corps est un `multipart/form-data` contenant une pièce avec un
`filename=` est rejetée par un **403 HTML, avant Django**. Mesuré en
production, à l'octet près :

    même corps, Content-Type: multipart/form-data  -> 403 LiteSpeed
    même corps, Content-Type: application/octet-stream -> la requête arrive

Le filtre ne regarde donc pas le contenu : il n'analyse le corps que lorsque
l'en-tête annonce un formulaire. Le nom du champ, l'extension et le type
MIME de la pièce ne changent rien, la taille non plus (testé de 100 octets à
500 Ko).

D'où ce parseur. Le client envoie **le corps multipart inchangé**, mais
étiqueté `application/octet-stream`, et place la frontière dans un en-tête
à part — un paramètre `boundary` sur un type inattendu étant trop
susceptible d'être rogné par un intermédiaire. Ici on remet l'étiquette
d'origine et l'on confie les octets au parseur de Django : aucune vue ne
change, `request.FILES` et `request.data` sont exactement ce qu'ils étaient.

Le `multipart/form-data` normal reste accepté partout : c'est ce
qu'utilisent l'admin Django, les tests et un éventuel hébergeur sans ce
filtre. Ce parseur est une voie de secours, pas un remplacement.
"""
import re

from rest_framework.exceptions import ParseError
from rest_framework.parsers import MultiPartParser

# La frontière est fabriquée par notre propre client : pas de raison
# d'accepter tout le jeu de caractères de la RFC 2046. Restreindre évite
# d'avoir à la citer dans l'en-tête reconstruit, donc toute possibilité
# d'y glisser un `;` ou un guillemet.
BOUNDARY_HEADER = "X-Upload-Boundary"
_BOUNDARY_RE = re.compile(r"[A-Za-z0-9_-]{8,70}")


class WrappedMultiPartParser(MultiPartParser):
    """Un corps multipart déguisé en flux binaire, remis à l'endroit."""

    media_type = "application/octet-stream"

    def parse(self, stream, media_type=None, parser_context=None):
        parser_context = parser_context or {}
        request = parser_context["request"]
        boundary = request.META.get("HTTP_X_UPLOAD_BOUNDARY", "")

        # Donnée venue du navigateur : elle finit dans l'en-tête que lit le
        # parseur de Django, donc elle est validée avant tout usage.
        if not _BOUNDARY_RE.fullmatch(boundary):
            raise ParseError(
                f"En-tête {BOUNDARY_HEADER} absent ou invalide : "
                "ce point d'entrée attend un corps multipart encapsulé."
            )

        return super().parse(
            stream,
            media_type=f"multipart/form-data; boundary={boundary}",
            parser_context=parser_context,
        )
