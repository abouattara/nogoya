"""Production settings: security hardening on top of base."""
from .base import *  # noqa: F401,F403
from .base import USE_S3, env

DEBUG = False

# Fail fast if the secret/hosts are not configured in the environment.
SECRET_KEY = env("DJANGO_SECRET_KEY")
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS")

# HTTPS / cookies. Redirect is opt-out so a plain-HTTP deployment (local
# `docker compose`, or a platform that terminates TLS upstream without
# forwarding X-Forwarded-Proto) doesn't end up in a redirect loop.
SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

# HSTS
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Misc headers
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

CSRF_TRUSTED_ORIGINS = env.list(
    "DJANGO_CSRF_TRUSTED_ORIGINS",
    default=env.list("CSRF_TRUSTED_ORIGINS", default=[]),
)

# Static files via WhiteNoise. Only the *static* backend is overridden here:
# the media backend stays whatever base.py chose (S3/R2 when USE_S3=True),
# otherwise production would silently fall back to the local filesystem.
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")  # noqa: F405
STORAGES = {
    **STORAGES,  # noqa: F405
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
    },
}

if not USE_S3:
    import warnings

    warnings.warn(
        "USE_S3 is disabled: media files go to the local filesystem. That is "
        "fine on a host with a persistent disk (shared hosting, VPS), and "
        "loses every upload on redeploy anywhere containerised. See "
        "STORAGE.md.",
        stacklevel=2,
    )

# Real SMTP in production
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
