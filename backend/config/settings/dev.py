"""Development settings."""
from .base import *  # noqa: F401,F403
from .base import env

DEBUG = True

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
