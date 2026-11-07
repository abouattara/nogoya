"""L'envoi d'une notification push, via Firebase Cloud Messaging.

Écrit sur la bibliothèque standard plus `PyJWT`, déjà présent. Les SDK
Google tirent une dizaine de paquets et des binaires compilés, ce qui est
cher à installer sur l'hébergement mutualisé où ce projet tourne, pour
deux appels HTTP et une signature RS256.

**Rien n'est commité.** Le compte de service vit dans un fichier dont
seul le chemin passe par l'environnement :

    FCM_CREDENTIALS_FILE=/home/binogoya/secrets/fcm-service-account.json
    FCM_PROJECT_ID=binogoya-xxxxx

Sans ces deux valeurs, l'envoi ne fait rien et le dit une fois dans le
journal. C'est délibéré : le site et l'application doivent fonctionner
entièrement sans Firebase, qui n'ajoute qu'une alerte quand
l'application est fermée.
"""
import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import jwt
from django.conf import settings

logger = logging.getLogger("nogoya.push")

TOKEN_URL = "https://oauth2.googleapis.com/token"
SCOPE = "https://www.googleapis.com/auth/firebase.messaging"
SEND_URL = "https://fcm.googleapis.com/v1/projects/{project}/messages:send"

# Le jeton d'accès dure une heure. On le garde en mémoire du processus :
# le redemander à chaque message ajouterait un aller-retour réseau par
# notification, et Google limite ces échanges.
_cached_token = {"value": None, "expires_at": 0.0}

# Pour ne pas répéter « Firebase n'est pas configuré » à chaque message.
_warned = False


def _credentials():
    """Le compte de service, ou None si Firebase n'est pas configuré."""
    global _warned
    path = getattr(settings, "FCM_CREDENTIALS_FILE", "")
    project = getattr(settings, "FCM_PROJECT_ID", "")
    if not path or not project:
        if not _warned:
            logger.info(
                "Firebase n'est pas configuré (FCM_CREDENTIALS_FILE / "
                "FCM_PROJECT_ID absents) : aucune notification push ne part. "
                "Le reste du service fonctionne normalement."
            )
            _warned = True
        return None

    file = Path(path)
    if not file.is_file():
        logger.error("FCM_CREDENTIALS_FILE pointe sur un fichier absent : %s", path)
        return None

    try:
        return json.loads(file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.error("Compte de service Firebase illisible : %s", exc)
        return None


def _access_token():
    """Échange le compte de service contre un jeton d'accès OAuth2."""
    now = time.time()
    # Trente secondes de marge : un jeton qui expire pendant le vol de la
    # requête donnerait un 401 que personne ne saurait expliquer.
    if _cached_token["value"] and _cached_token["expires_at"] > now + 30:
        return _cached_token["value"]

    credentials = _credentials()
    if credentials is None:
        return None

    assertion = jwt.encode(
        {
            "iss": credentials["client_email"],
            "scope": SCOPE,
            "aud": TOKEN_URL,
            "iat": int(now),
            "exp": int(now) + 3600,
        },
        credentials["private_key"],
        algorithm="RS256",
    )

    body = urllib.parse.urlencode(
        {
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": assertion,
        }
    ).encode()

    request = urllib.request.Request(
        TOKEN_URL,
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            payload = json.loads(response.read())
    except (urllib.error.URLError, json.JSONDecodeError, OSError) as exc:
        logger.error("Jeton Firebase refusé : %s", exc)
        return None

    _cached_token["value"] = payload.get("access_token")
    _cached_token["expires_at"] = now + float(payload.get("expires_in", 3600))
    return _cached_token["value"]


def send_to_tokens(tokens, *, title, body, data=None):
    """Envoie une notification, et renvoie les jetons que FCM a rejetés.

    Un jeton rejeté n'est pas une panne : l'application a été
    désinstallée, ou le jeton a tourné. L'appelant les supprime, sinon la
    table grossit indéfiniment d'appareils qui n'existent plus.
    """
    tokens = [token for token in tokens if token]
    if not tokens:
        return []

    access = _access_token()
    if access is None:
        return []

    project = settings.FCM_PROJECT_ID
    url = SEND_URL.format(project=project)
    headers = {
        "Authorization": f"Bearer {access}",
        "Content-Type": "application/json; charset=UTF-8",
    }
    # Les données d'un message FCM doivent être des chaînes : un entier
    # passe silencieusement à la trappe côté Android.
    payload_data = {str(k): str(v) for k, v in (data or {}).items()}

    invalid = []
    for token in tokens:
        message = {
            "message": {
                "token": token,
                "notification": {"title": title, "body": body},
                "data": payload_data,
                "android": {"priority": "high"},
            }
        }
        request = urllib.request.Request(
            url, data=json.dumps(message).encode(), headers=headers
        )
        try:
            with urllib.request.urlopen(request, timeout=10):
                pass
        except urllib.error.HTTPError as exc:
            # 404 UNREGISTERED et 400 INVALID_ARGUMENT désignent un jeton
            # mort. Tout le reste est un incident de notre côté.
            if exc.code in (400, 403, 404):
                invalid.append(token)
                logger.info("Jeton d'appareil périmé, retiré (%s)", exc.code)
            else:
                logger.error("Envoi push en échec (%s)", exc.code)
        except (urllib.error.URLError, OSError) as exc:
            logger.error("Envoi push injoignable : %s", exc)

    return invalid


def send_to_user(user, *, title, body, data=None):
    """Prévient tous les appareils d'une personne, et fait le ménage."""
    from .models import DeviceToken

    if user is None:
        return

    tokens = list(
        DeviceToken.objects.filter(user=user).values_list("token", flat=True)
    )
    invalid = send_to_tokens(tokens, title=title, body=body, data=data)
    if invalid:
        DeviceToken.objects.filter(token__in=invalid).delete()
