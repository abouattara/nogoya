# NOGOYA — backend

API REST pour la marketplace nogoya. Le frontend (Next.js) vit dans
`../frontend` — voir `../ARCHITECTURE.md` pour la vue d'ensemble et
l'historique de la décision de pivot (Django templates → API + Next.js).

**Stack :** Django 6 · DRF · SimpleJWT · PostgreSQL 16 · Redis · Channels · Celery.

## Prérequis
- Python 3.14
- PostgreSQL 16 (service `postgresql-x64-16`)
- Redis / Memurai (service `Memurai`)

## Installation (dev)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements/dev.txt

# Config : créer .env à partir de .env.example
copy .env.example .env    # puis générer une vraie SECRET_KEY

python manage.py migrate
python manage.py runserver
```

API : http://127.0.0.1:8000/api/v1/ · Admin : /admin/ · Santé : /healthz/ · /readyz/

## Données de démo
```powershell
python manage.py seed_demo
```
Crée des catégories, 2 fournisseurs, un visiteur et 10 produits approuvés
avec image (mot de passe `DemoPass123!`). Idempotent.

## Structure
```
config/            # projet Django (settings base/dev/prod, urls, asgi, wsgi, celery)
apps/
  core/            # base commune (TimeStampedModel, home, healthz)
  ...              # accounts, catalog, suppliers, reviews, messaging, notifications (par phase)
templates/         # templates + base Tailwind
static/  media/
requirements/      # base.txt / dev.txt / prod.txt
SUIVI.md           # suivi de projet (statuts par phase)
```

## Tests
```powershell
python manage.py test
```

## Sécurité
Aucun secret dans le code : tout passe par variables d'environnement (`.env` non commité).
Voir `SUIVI.md` pour les décisions techniques et l'état d'avancement.
