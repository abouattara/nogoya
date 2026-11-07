"""Development settings."""
import sys

from .base import *  # noqa: F401,F403
from .base import env

DEBUG = True

# ---------------------------------------------------------------------------
# L'émulateur Android fait partie du poste de développement
# ---------------------------------------------------------------------------
# Un émulateur Android joint le `localhost` de la machine hôte par
# l'adresse 10.0.2.2, et envoie donc `Host: 10.0.2.2:8000`. Django la
# refusait avec un 400 « DisallowedHost », que l'application mobile ne
# pouvait lire autrement que comme « les informations envoyées ne sont pas
# valides » : un message juste, qui désignait le mauvais coupable.
#
# L'ajout vaut pour le développement seulement. `base.py` continue de lire
# `DJANGO_ALLOWED_HOSTS` depuis l'environnement, et la production n'a
# aucune raison de connaître cette adresse.
ALLOWED_HOSTS = list(ALLOWED_HOSTS) + ["10.0.2.2", "0.0.0.0", "testserver"]  # noqa: F405

# ---------------------------------------------------------------------------
# Le développement local ne dépend pas d'un Redis vivant
# ---------------------------------------------------------------------------
# `base.py` met le cache sur Redis, et la limitation de débit le traverse à
# *chaque* requête : sans Redis, le serveur de développement répond 500 sur
# toutes les URL, y compris la page d'accueil. Redis arrive normalement par
# `docker compose`, mais tout le monde ne fait pas tourner Docker pour
# relire une page — et lancer le projet ne doit pas réclamer un service
# qu'on n'a pas installé.
#
# Un cache en mémoire suffit en local. Qui veut éprouver le vrai cache
# partagé met `USE_REDIS_CACHE=True` dans son `.env`.
if not env.bool("USE_REDIS_CACHE", default=False):
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "nogoya-dev",
        }
    }

# ---------------------------------------------------------------------------
# Les tests non plus
# ---------------------------------------------------------------------------
# `base.py` met le cache sur Redis, et la limitation de débit traverse le
# cache à *chaque* requête : sans Redis, la suite entière échoue sur
# « Connection refused », y compris des tests qui n'ont rien à voir avec le
# cache. On l'a découvert le jour où le Redis local s'est arrêté — 25 tests
# de messagerie rouges, et la trace ne nommait que `redis/connection.py`.
#
# Un cache en mémoire suffit : la suite tourne dans un seul processus, donc
# les compteurs de débit et la déduplication des vues se comportent comme
# avec un cache partagé. Et la suite devient exécutable n'importe où, y
# compris en intégration continue.
if "test" in sys.argv:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "nogoya-tests",
        }
    }

# Email printed to the console in dev (no real SMTP needed).
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Show detailed toolbar-style errors only locally.
INTERNAL_IPS = ["127.0.0.1"]

# Optionally run Celery tasks synchronously in dev when no worker is running.
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=True)

# Any local port may host the frontend during development: `next dev` on
# 3000, the E2E production build on 3100, a second branch on 3001...
# Pinning a single origin made the browser silently block /auth/me/ and log
# the user out. Production keeps the strict explicit list from base.py.
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^http://localhost:\d+$",
    r"^http://127\.0\.0\.1:\d+$",
]
