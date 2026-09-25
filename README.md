# nogoya

Marketplace de location et de vente entre particuliers et professionnels :
véhicules, logements, équipements, outils, électronique, mobilier, matériel
événementiel, agricole et professionnel.

**Stack** — Next.js 16 (App Router, TypeScript, Tailwind v4) · Django 6 +
Django REST Framework · PostgreSQL 16 · Redis · Celery · stockage
S3-compatible (MinIO en local, Cloudflare R2 en production).

## Démarrage rapide

### Avec Docker (tout compris)

```bash
cp backend/.env.example backend/.env    # puis renseigner DJANGO_SECRET_KEY
docker compose up --build
docker compose exec backend python manage.py seed_demo
```

- Frontend : http://localhost:3000
- API : http://localhost:8000/api/v1/ — Admin : http://localhost:8000/admin/
- MinIO (console) : http://localhost:9001

### Sans Docker

Prérequis : Python 3.13+, Node 24+, PostgreSQL 16, Redis (Memurai sous
Windows).

```bash
# Backend
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # source .venv/bin/activate sous Unix
pip install -r requirements/dev.txt
cp .env.example .env                   # renseigner DJANGO_SECRET_KEY et DATABASE_URL
python manage.py migrate
python manage.py seed_demo             # données de démonstration
python manage.py runserver 127.0.0.1:8000

# Frontend (autre terminal)
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

### Comptes de démonstration

Mot de passe `DemoPass123!` :

| Rôle | Téléphone |
|---|---|
| Fournisseur | `+22670010001`, `+22670010002` |
| Visiteur | `+22670020001` |

## Fonctionnalités

**Marketplace** — recherche plein texte, filtres (catégorie, ville, type,
prix) et **filtres par caractéristique** propres à chaque catégorie, tri,
pagination, fiche produit avec galerie, catalogue fournisseur filtrable.

**Annonces** — création et **modification après publication** (slug
préservé), galerie multi-images avec réorganisation et choix de l'image
principale, **éditeur d'image intégré** (recadrage, rotation, miroir, zoom,
formats 1:1 / 4:3 / 16:9) disponible avant comme après publication,
**attributs dynamiques par catégorie** administrables sans migration.

**Localisation** — saisie manuelle, géolocalisation navigateur optionnelle,
choix entre position exacte et approximative, lien Google Maps généré sans
clé API.

**Échanges** — messagerie interne avec pièces jointes produit et
**messages vocaux** (enregistrement `MediaRecorder`, lecteur avec
progression, validation et accès contrôlés côté serveur), blocage et
signalement, contact téléphone réservé aux utilisateurs connectés, WhatsApp
en option activée par le fournisseur, partage avec aperçu Open Graph.

**Découverte** — favoris, historique de consultation, recherches récentes,
recommandations (catégories consultées + favoris + ville), nouveautés,
notifications avec cloche et compteur.

**Fournisseur** — tableau de bord avec tuiles, **graphiques** (vues,
contacts, messages sur 7/30/90 jours), répartition des annonces, top
annonces et catégories.

**Live** — modèles et API complets (sessions, spectateurs, chat, produits
épinglés) ; l'intégration vidéo reste à brancher (voir LIVE.md).

## Tests

```bash
cd backend  && python manage.py test        # 121 tests
cd frontend && npm test                     # 65 tests composants (Vitest)
cd frontend && npm run test:e2e             # 18 parcours (Playwright, desktop + mobile)
```

Détails et prérequis : [TESTING.md](TESTING.md).

## Documentation

| Fichier | Contenu |
|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | choix techniques et décisions structurantes |
| [PRODUCT_SPEC.md](PRODUCT_SPEC.md) | périmètre produit et parcours |
| [API.md](API.md) | tous les endpoints REST |
| [DATABASE.md](DATABASE.md) | schéma, index, migrations |
| [STORAGE.md](STORAGE.md) | S3 / MinIO / R2, pipeline images et audio |
| [SECURITY.md](SECURITY.md) | authentification, permissions, uploads, vie privée |
| [TESTING.md](TESTING.md) | stratégie de tests |
| [DEPLOYMENT.md](DEPLOYMENT.md) | environnements, Docker, mise en production |
| [DEPLOYMENT-CPANEL.md](DEPLOYMENT-CPANEL.md) | mise en ligne sur un hébergement mutualisé cPanel |
| [LIVE.md](LIVE.md) | modèles live et intégration vidéo future |
| [TODO.md](TODO.md) | audit d'avancement, ce qui reste |

## Structure

```
backend/    Django + DRF (API, admin, modération)
frontend/   Next.js (App Router)
docker-compose.yml
nog-prog/   ancien projet — référence visuelle, ne pas modifier
```
