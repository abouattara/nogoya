"""Development settings."""
import sys

from .base import *  # noqa: F401,F403
from .base import env

DEBUG = True

# ---------------------------------------------------------------------------
# Les tests ne dépendent pas d'un Redis vivant
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
