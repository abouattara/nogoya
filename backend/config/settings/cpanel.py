"""Réglages pour un hébergement mutualisé cPanel (AshuraHosting).

Repart de `prod.py` — mêmes protections HTTPS, HSTS, cookies — et remplace
ce qu'un mutualisé ne fournit pas :

* **Pas de Redis.** Le cache passe sur une table PostgreSQL/MySQL. Ce n'est
  pas un détail de confort : la déduplication des vues et les quotas de
  débit *s'appuient* sur le cache. Avec un cache en mémoire, chaque worker
  Passenger aurait le sien, et un quota de 20 connexions/minute deviendrait
  20 × le nombre de workers. Une table partagée reste correcte.
* **Pas de worker persistant.** Celery s'exécute en mode « eager » : le
  traitement d'image se fait dans la requête. Il dure environ une seconde
  pour une photo de téléphone — acceptable ici, et c'est de toute façon la
  seule option sans processus long.
* **Pas de stockage objet.** Les médias vont sur le disque du compte, qui
  est persistant sur un mutualisé (contrairement à un conteneur). Basculer
  vers S3/R2 plus tard ne demande que `USE_S3=True` et les clés.

Activation : `DJANGO_SETTINGS_MODULE=config.settings.cpanel`
"""
from .prod import *  # noqa: F401,F403
from .prod import DATABASES, INSTALLED_APPS, env

# Passenger sert l'application en WSGI : le serveur ASGI n'a rien à faire
# ici, et ses dépendances (twisted, autobahn…) pèsent pour rien sur le
# quota disque du compte.
INSTALLED_APPS = [app for app in INSTALLED_APPS if app != "daphne"]

# ---------------------------------------------------------------------------
# MySQL / MariaDB
# ---------------------------------------------------------------------------
if "mysql" in DATABASES["default"]["ENGINE"]:
    DATABASES["default"].setdefault("OPTIONS", {})
    DATABASES["default"]["OPTIONS"].update(
        {
            "charset": "utf8mb4",
            # Sans le mode strict, MySQL tronque silencieusement une valeur
            # trop longue au lieu de refuser l'écriture.
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
        }
    )

    # Les graphiques du tableau de bord regroupent par jour (`TruncDate`).
    # Sur MySQL, dès que le fuseau de Django diffère de celui de la
    # connexion, Django écrit CONVERT_TZ(col, 'UTC', 'Africa/Ouagadougou') —
    # qui renvoie **NULL** tant que les tables de fuseaux horaires ne sont
    # pas chargées dans MySQL (`mysql_tzinfo_to_sql`), ce qu'un mutualisé ne
    # permet jamais. Les statistiques seraient vides sans la moindre erreur.
    #
    # Le Burkina Faso est à UTC+0 toute l'année, sans heure d'été : passer
    # en UTC ne décale donc *aucune* heure affichée, et supprime l'appel à
    # CONVERT_TZ puisque les deux fuseaux coïncident.
    TIME_ZONE = "UTC"

# ---------------------------------------------------------------------------
# Cache : table de base de données plutôt que Redis
# ---------------------------------------------------------------------------
# À créer une fois : python manage.py createcachetable
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": env("CACHE_TABLE", default="nogoya_cache"),
        # Le cache sert surtout de compteur court (vues, quotas) : on le
        # borne pour qu'il ne grossisse pas indéfiniment.
        "OPTIONS": {"MAX_ENTRIES": 10_000, "CULL_FREQUENCY": 3},
    },
}

# ---------------------------------------------------------------------------
# Tâches asynchrones : exécutées dans la requête
# ---------------------------------------------------------------------------
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = False  # une vignette ratée ne casse pas l'upload

# ---------------------------------------------------------------------------
# Redirection HTTPS
# ---------------------------------------------------------------------------
# cPanel termine le TLS en amont et transmet X-Forwarded-Proto ; la
# redirection est donc sûre. Si l'hébergeur ne transmet pas cet en-tête, la
# redirection boucle : mettre alors DJANGO_SECURE_SSL_REDIRECT=False et
# laisser le .htaccess forcer le HTTPS.
SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
