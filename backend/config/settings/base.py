"""
Base settings shared by all environments.

Everything secret or environment-specific comes from environment variables
(via django-environ). No secret is ever hard-coded here.
"""
from pathlib import Path

import environ

# BASE_DIR points to the project root (folder containing manage.py).
BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
# Load .env if present (dev convenience). In prod, real env vars take priority.
environ.Env.read_env(BASE_DIR / ".env")

# ---------------------------------------------------------------------------
# Core security (values overridden per environment)
# ---------------------------------------------------------------------------
SECRET_KEY = env("DJANGO_SECRET_KEY", default="unsafe-dev-key-override-me")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------
DJANGO_APPS = [
    "daphne",  # ASGI server, must precede staticfiles
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_filters",
    "drf_spectacular",
    "storages",
]

LOCAL_APPS = [
    "apps.core",
    "apps.accounts",
    "apps.suppliers",
    "apps.catalog",
    "apps.analytics",
    "apps.messaging",
    "apps.media",
    "apps.notifications",
    "apps.live",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.core.middleware.VisitorCookieMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        # No project templates any more: the interface is the Next.js
        # frontend. APP_DIRS stays on for the Django admin's own templates.
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# ---------------------------------------------------------------------------
# Database (PostgreSQL via DATABASE_URL)
# ---------------------------------------------------------------------------
DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default="postgres://postgres:postgres@127.0.0.1:5432/nogoya",
    ),
}

# ---------------------------------------------------------------------------
# Redis: cache, channel layer, Celery broker
# ---------------------------------------------------------------------------
REDIS_URL = env("REDIS_URL", default="redis://127.0.0.1:6379/0")

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
    },
}

CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://127.0.0.1:6379/1")
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=False)

# ---------------------------------------------------------------------------
# Authentication: custom user authenticated by phone number.
# The default ModelBackend authenticates on USERNAME_FIELD (== phone),
# so no custom backend is required.
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = "accounts.User"
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "core:home"
LOGOUT_REDIRECT_URL = "core:home"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------------
# I18N / TZ
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "fr"
TIME_ZONE = "Africa/Ouagadougou"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static & media
# ---------------------------------------------------------------------------
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# ---------------------------------------------------------------------------
# Object storage (S3-compatible). Set USE_S3=True to switch media files from
# the local filesystem to any S3 API: AWS S3, Cloudflare R2 or a local MinIO.
# Nothing in the application code knows which one is in use — see STORAGE.md.
# ---------------------------------------------------------------------------
USE_S3 = env.bool("USE_S3", default=False)

if USE_S3:
    AWS_ACCESS_KEY_ID = env("S3_ACCESS_KEY")
    AWS_SECRET_ACCESS_KEY = env("S3_SECRET_KEY")
    AWS_STORAGE_BUCKET_NAME = env("S3_BUCKET")
    AWS_S3_ENDPOINT_URL = env("S3_ENDPOINT", default=None)
    AWS_S3_REGION_NAME = env("S3_REGION", default="auto")
    # Public read for product images; audio is served through signed URLs
    # generated by the messaging API (see apps/messaging/api.py).
    AWS_QUERYSTRING_AUTH = False
    AWS_S3_FILE_OVERWRITE = False
    AWS_DEFAULT_ACL = None
    AWS_S3_ADDRESSING_STYLE = env("S3_ADDRESSING_STYLE", default="path")
    # Public base URL (CDN in front of the bucket when available).
    AWS_S3_CUSTOM_DOMAIN = env("S3_PUBLIC_DOMAIN", default=None)
    # Uploaded names are random and never overwritten, so objects are
    # immutable: let the CDN keep them instead of revalidating every time.
    AWS_S3_OBJECT_PARAMETERS = {"CacheControl": "public, max-age=31536000, immutable"}

    STORAGES = {
        "default": {"BACKEND": "storages.backends.s3.S3Storage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
else:
    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Upload limits (enforced again per-endpoint in serializers)
# ---------------------------------------------------------------------------
# Ceilings on what reaches the server. The browser already shrinks images
# and refuses long videos, but a client is only ever a convenience: these
# are the numbers that protect the bucket bill.
MAX_IMAGE_UPLOAD_BYTES = env.int("MAX_IMAGE_UPLOAD_BYTES", default=12 * 1024 * 1024)
MAX_AUDIO_UPLOAD_BYTES = env.int("MAX_AUDIO_UPLOAD_BYTES", default=10 * 1024 * 1024)
MAX_VIDEO_UPLOAD_BYTES = env.int("MAX_VIDEO_UPLOAD_BYTES", default=100 * 1024 * 1024)

MAX_AUDIO_DURATION_SECONDS = env.int("MAX_AUDIO_DURATION_SECONDS", default=300)
# One minute of video is plenty to show an item and keeps a message under a
# few MB once the phone has encoded it.
MAX_VIDEO_DURATION_SECONDS = env.int("MAX_VIDEO_DURATION_SECONDS", default=60)

# How many media files one chat message may carry.
MAX_ATTACHMENTS_PER_MESSAGE = env.int("MAX_ATTACHMENTS_PER_MESSAGE", default=6)

# Uploads abandoned before their message exists are swept after this delay.
ORPHAN_MEDIA_RETENTION_HOURS = env.int("ORPHAN_MEDIA_RETENTION_HOURS", default=24)

# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="NOGOYA <no-reply@nogoya.local>")

# ---------------------------------------------------------------------------
# DRF — the Next.js frontend talks to this API exclusively (JWT).
# SessionAuthentication is kept only so the browsable API works with the
# Django admin session while developing.
# ---------------------------------------------------------------------------
from datetime import timedelta  # noqa: E402

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_CLASSES": [
        "apps.core.throttling.VisitorScopedRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
        # Not AnonRateThrottle: it keys on the IP, and with server-side
        # rendering every anonymous request shares the frontend server's
        # address. See apps/core/throttling.py.
        "apps.core.throttling.VisitorRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "auth": "20/min",       # login / inscription (credential stuffing)
        "search": "120/min",    # listing endpoint, scraping of the catalogue
        "user": "600/min",      # signed-in baseline, generous on purpose
        "visitor": "300/min",   # per browser, not per IP
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=14),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Nogoya API",
    "DESCRIPTION": "API de la marketplace de location/vente Nogoya.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# Public address of the Next.js frontend: used for the admin's "view on site"
# links and for any URL we hand to a human.
FRONTEND_URL = env("FRONTEND_URL", default="http://localhost:3000").rstrip("/")

# CORS: only the Next.js frontend (dev + configured prod origins) may call the API.
from corsheaders.defaults import default_headers as cors_default_headers  # noqa: E402

CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS", default=["http://localhost:3000"]
)
CORS_ALLOW_CREDENTIALS = True
# The anonymous visitor id travels as a header (see apps.core.middleware).
CORS_ALLOW_HEADERS = (*cors_default_headers, "x-visitor-id")

# ---------------------------------------------------------------------------
# Logging (console; replaces the old print() debugging)
# ---------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {"format": "[{levelname}] {asctime} {name}: {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "verbose"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "nogoya": {"handlers": ["console"], "level": "DEBUG", "propagate": False},
    },
}
