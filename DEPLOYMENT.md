# Déploiement — nogoya

Trois environnements : `development`, `staging`, `production`. Le code est
identique partout ; seules les variables d'environnement changent.

> **Hébergement mutualisé cPanel ?** Ce document suppose un VPS ou une
> plateforme conteneurisée (Docker, Redis managé, stockage objet). Pour un
> mutualisé, la procédure et les compromis sont dans
> [DEPLOYMENT-CPANEL.md](DEPLOYMENT-CPANEL.md).

## Architecture cible (faible coût)

```
Navigateur
    │
    ├── Frontend Next.js ......... Vercel (plan Hobby/Pro)
    │        │
    │        └── SSR → API Django (server-to-server)
    │
    ├── Backend Django + Daphne .. Railway / Render / VPS (~5-10 $/mois)
    │        ├── PostgreSQL managé (Neon, Supabase, Railway)
    │        └── Redis managé (Upstash — offre gratuite suffisante au MVP)
    │
    └── Images & vocaux .......... Cloudflare R2 (pas de frais de sortie)
                 └── CDN Cloudflare devant le bucket
```

Pourquoi ce découpage :

- **Vercel** pour le frontend : build Next.js natif, CDN mondial, gratuit
  au démarrage.
- **R2 plutôt que S3** : une marketplace sert beaucoup d'images ; les frais
  d'egress sont le poste qui dérape en premier, et R2 les supprime.
- **Redis managé** : nécessaire (cache de déduplication des vues, quotas de
  débit, broker Celery) mais léger — l'offre gratuite d'Upstash suffit
  largement au MVP. Plus de couche Channels : elle a été retirée avec les
  WebSockets qui n'existaient pas.
- **Celery** : un seul worker `--pool=solo` suffit (traitement des images).

## Variables d'environnement

### Backend (obligatoires en production)

```bash
DJANGO_SETTINGS_MODULE=config.settings.prod
DJANGO_SECRET_KEY=<50+ caractères aléatoires, jamais commité>
DJANGO_ALLOWED_HOSTS=api.nogoya.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://nogoya.com,https://api.nogoya.com
CORS_ALLOWED_ORIGINS=https://nogoya.com

DATABASE_URL=postgres://user:pass@host:5432/nogoya
REDIS_URL=rediss://...upstash.io:6379
CELERY_BROKER_URL=rediss://...upstash.io:6379

USE_S3=True
S3_ENDPOINT=https://<account>.r2.cloudflarestorage.com
S3_BUCKET=nogoya-media
S3_ACCESS_KEY=...
S3_SECRET_KEY=...
S3_REGION=auto
S3_ADDRESSING_STYLE=virtual
S3_PUBLIC_DOMAIN=media.nogoya.com

EMAIL_HOST=...
DEFAULT_FROM_EMAIL=nogoya <no-reply@nogoya.com>
```

`DJANGO_SECURE_SSL_REDIRECT=False` uniquement si la plateforme termine TLS
sans transmettre `X-Forwarded-Proto` (sinon boucle de redirection).

### Frontend

```bash
API_URL=https://api.nogoya.com              # appels serveur-à-serveur (SSR)
NEXT_PUBLIC_API_URL=https://api.nogoya.com  # appels navigateur (injecté au build)
S3_PUBLIC_HOST=media.nogoya.com             # autorise le domaine pour next/image
```

`NEXT_PUBLIC_API_URL` est figée au moment du build : changer de domaine
d'API impose un rebuild du frontend.

## Docker (local et VPS)

```bash
docker compose up --build        # démarre db, redis, minio, backend, celery, frontend
docker compose exec backend python manage.py createsuperuser
docker compose exec backend python manage.py seed_demo
docker compose down              # arrêt
docker compose down -v           # arrêt + suppression des volumes (données perdues)
```

Les migrations et `collectstatic` sont lancés automatiquement au démarrage
du conteneur `backend`.

Ports exposés : frontend 3000, backend 8000, MinIO 9000/9001, PostgreSQL
**5433** et Redis **6380** (décalés pour ne pas entrer en conflit avec une
instance locale).

## Première mise en production

1. Provisionner PostgreSQL, Redis et le bucket R2.
2. Déployer le backend (image `backend/Dockerfile`, ou buildpack Python +
   `daphne -b 0.0.0.0 -p $PORT config.asgi:application`).
3. `python manage.py migrate` puis `createsuperuser`.
4. Créer les catégories et leurs attributs via `/admin/` (ou lancer
   `seed_demo` sur un environnement de démonstration uniquement).
5. Déployer le frontend avec les variables ci-dessus.
6. Vérifier `/healthz/` et `/readyz/`, puis le parcours inscription →
   annonce → recherche.

## Health checks

| Endpoint | Réponse | Usage |
|---|---|---|
| `/healthz/` | `{"status": "ok"}` | liveness — l'application répond |
| `/readyz/` | état PostgreSQL + cache, 503 si dégradé | readiness — prêt à recevoir du trafic |

Aucun des deux n'expose de version, de chemin ni de détail
d'infrastructure.

## Limitation de débit et protection au bord

L'API applique ses propres quotas (connexion, recherche, utilisateur,
visiteur — voir SECURITY.md). Ils sont comptés **par navigateur**, jamais
par IP : le rendu serveur fait arriver tout le trafic anonyme depuis
l'adresse du frontend.

C'est un garde-fou applicatif, pas un bouclier. En production, activer
devant le domaine :

- Cloudflare (proxy orange) avec « Bot Fight Mode » et une *rate limiting
  rule* sur `/api/v1/auth/*` (par exemple 30 requêtes / 10 min / IP) ;
- le pare-feu du VPS limité à 80/443 et au port SSH.

Un attaquant qui fait tourner son identifiant visiteur contourne la limite
applicative exactement comme il contournerait une limite par IP en changeant
d'adresse : ces deux couches se complètent, aucune ne remplace l'autre.

## Entretien du stockage

Les fichiers ne disparaissent pas tout seuls. À planifier une fois par jour,
hors heures de pointe :

```bash
python manage.py prune_media --delete
```

Elle compare le bucket à la base et supprime ce que plus aucune ligne ne
référence : uploads interrompus, médias de messages supprimés, restes d'une
version antérieure. Les fichiers de moins de 24 h sont épargnés (un upload
en cours appartient à une requête qui n'a pas encore validé).

Lancer d'abord **sans** `--delete` : la commande affiche ce qu'elle
supprimerait. C'est la seule commande du projet qui détruit des données.

| Planificateur | Entrée |
|---|---|
| cron | `15 3 * * * cd /srv/nogoya/backend && .venv/bin/python manage.py prune_media --delete` |
| systemd | un `timer` quotidien sur la même commande |
| Docker | `docker compose exec backend python manage.py prune_media --delete` |

## Sauvegardes

- **PostgreSQL** : sauvegarde quotidienne automatique du fournisseur managé,
  rétention 7 jours minimum. `pg_dump` hebdomadaire archivé sur R2 pour une
  copie hors plateforme.
- **Restauration** : à tester au moins une fois par trimestre sur un
  environnement jetable (`pg_restore` puis parcours de connexion).
- **Objets (R2)** : activer le versioning du bucket ; les images sont
  irrécupérables autrement.

## CI

`.github/workflows/ci.yml` exécute lint → typecheck → tests backend →
tests frontend → build → E2E. Un déploiement ne doit jamais partir d'un
pipeline rouge.
