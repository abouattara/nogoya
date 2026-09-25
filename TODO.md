# TODO — nogoya

Statuts : `DONE` / `IN PROGRESS` / `TODO`

## AUDIT FINAL (2026-09-23)

Statuts : **DONE** (implémenté et vérifié) / **PARTIALLY IMPLEMENTED**
(fonctionne, mais une partie de la demande manque — la raison est écrite) /
**BROKEN** (présent mais cassé) / **BLOCKED** (impossible à vérifier ici —
la raison exacte est écrite).

### Catalogue & annonces

| Fonctionnalité | Statut |
|---|---|
| Recherche / filtres / tri / pagination | DONE |
| Catalogue fournisseur public (`/fournisseurs/[id]`) | DONE |
| Détail annonce (galerie, description, localisation, carte) | DONE |
| Création d'annonce | DONE |
| Formulaire de création **multi-étapes** | PARTIALLY IMPLEMENTED — un seul écran scrollable, validé champ par champ. Fonctionnel, mais ce n'est pas le tunnel en étapes demandé. |
| Modification d'une annonce publiée (slug stable, retour en modération) | DONE |
| Gestion des images après publication (ajout / suppression / ordre / principale) | DONE |
| Éditeur d'image (recadrage, rotation, miroir, zoom, ratios 1:1/4:3/16:9) | DONE |
| Éditeur d'image : **filtres et détourage de fond** | PARTIALLY IMPLEMENTED — le pipeline canvas (`lib/image-editing.ts`) ne fait que géométrie ; aucun filtre colorimétrique ni suppression d'arrière-plan. |
| Attributs dynamiques par catégorie (définition, héritage, saisie, filtres) | DONE |
| Localisation : ville/région/pays, géolocalisation, lien Google Maps sans clé | DONE |
| Confidentialité de position (exacte / approximative, arrondi ~1 km serveur) | DONE |
| Réorganisation d'images en drag & drop | PARTIALLY IMPLEMENTED — boutons ← → ; l'ordre se change, mais sans glisser-déposer. |

### Interactions

| Fonctionnalité | Statut |
|---|---|
| Chat interne (conversations, blocage, signalement, non-lus) | DONE |
| Chat : **messages vocaux** (enregistrement, envoi, lecture, durée) | DONE |
| Chat : **images** (sélection, glisser-déposer, plusieurs par message, aperçu, retrait, compression, progression, annulation, galerie) | DONE |
| Chat : **vidéos** (sélection, aperçu, image d'aperçu, limites 60 s / 100 Mo, lecture à la demande) | DONE |
| Chat : **transcodage vidéo côté serveur** | NON IMPLÉMENTÉ — exigerait ffmpeg dans l'image Docker et un worker dédié. Les limites (60 s, 100 Mo) et l'encodage déjà fait par le téléphone tiennent lieu de garde-fou ; la couture est documentée dans STORAGE.md. |
| Chat : **nettoyage des fichiers** (signal de suppression + `prune_media`) | DONE |
| Chat : accès à l'audio réservé aux participants, validation par octets magiques, lecture via fetch authentifié | DONE — corrigé le 2026-09-23 : la « URL signée » S3 ne signait rien (`AWS_QUERYSTRING_AUTH = False`) et la lecture `<audio src>` partait sans jeton. L'API streame désormais les octets, et le bucket n'est public que sur `products/`. |
| Produit joint à un message | DONE |
| Chat temps réel par **WebSocket** | NON IMPLÉMENTÉ — le temps réel passe par polling TanStack Query (4 s). Channels a été **retiré** le 2026-09-24 : router des WebSockets sans aucun consumer coûtait deux dépendances et une couche Redis pour rien. Remise en place documentée dans ARCHITECTURE.md. |
| Sélecteur libre de produit à joindre côté visiteur | PARTIALLY IMPLEMENTED — le visiteur ne peut joindre que le produit d'origine de la conversation. |
| Favoris (bouton fiche + carte, page `/favoris`, filtre API) | DONE |
| Notifications (modèle générique, cloche, page, non-lues) | DONE |
| Contact téléphone (révélé aux connectés seulement) + WhatsApp opt-in | DONE |
| Partage (Web Share / copie / WhatsApp) + compteur | DONE |
| Commentaires produit | HORS PÉRIMÈTRE — exclu explicitement par le cahier des charges. |

### Découverte & statistiques

| Fonctionnalité | Statut |
|---|---|
| Dashboard fournisseur : tuiles (annonces, vues, contacts, messages non lus) | DONE |
| Dashboard fournisseur : **graphiques** (vues/contacts/messages dans le temps, top annonces, top catégories, 7/30/90 j) | DONE |
| Dashboard utilisateur : vus récemment, recherches récentes, suggestions, nouveautés | DONE |
| Recommandations (moteur à règles : historique + catégories + favoris + ville) | DONE |
| Recherches sans résultat journalisées (`SearchEvent.results_count`) | DONE |
| `DailyProductStats` (pré-agrégation) | PARTIALLY IMPLEMENTED — le modèle existe mais n'est jamais peuplé ; les graphiques agrègent directement `ProductView`/`ContactEvent` en SQL. Suffisant à cette volumétrie, à remplacer par une tâche Celery quand les tables grossiront. |
| Demande d'article (« je ne trouve pas ce que je cherche ») | NON IMPLÉMENTÉ — aucun modèle ni écran ; la recherche sans résultat est journalisée mais ne débouche sur aucune demande. |

### Live

| Fonctionnalité | Statut |
|---|---|
| Modèles `LiveSession` / `LiveViewer` / `LiveMessage` / `LiveProduct` + API (démarrer, terminer, épingler, chat, audience) | DONE |
| Interface Live (page spectateur, studio hôte, lecteur vidéo) | PARTIALLY IMPLEMENTED — backend et coutures fournisseur prêts (`provider`, `ingest_url`, `playback_url`), aucune UI : le streaming exige un prestataire externe non choisi. Voir LIVE.md. |

### Sécurité

| Fonctionnalité | Statut |
|---|---|
| Aucun secret dans le dépôt (tout en `.env`, `.env.example` documenté) | DONE |
| JWT access en mémoire + refresh en cookie httpOnly (BFF Next.js) | DONE |
| Rotation + blacklist du refresh, rafraîchissement concurrent sérialisé | DONE |
| Anti-IDOR testé (annonce, image, message, audio, conversation, stats, live) | DONE |
| Upload : taille, type MIME réel (PIL / octets magiques), durée audio | DONE |
| Identifiant visiteur validé côté serveur, jamais utilisé comme identité, régénéré à la déconnexion | DONE |
| Contraste : aucun texte blanc sur fond blanc (thème unique, `color-scheme: light`) | DONE |
| Health checks sans information sensible (`{"status": …}` + état DB/cache) | DONE |
| Rate limiting (auth, recherche, utilisateur, visiteur) | DONE — le scope `search` était déclaré mais appliqué à aucune vue ; il l'est désormais sur la liste d'annonces, et l'anonyme est compté **par navigateur** (pas par IP, que le rendu serveur rend inutilisable). |
| Mot de passe oublié (OTP / e-mail) | NON IMPLÉMENTÉ — aucun canal d'envoi (SMS/e-mail) n'est provisionné. |

### Tests & industrialisation

| Fonctionnalité | Statut |
|---|---|
| Tests backend | DONE — 121 tests |
| Tests frontend (Vitest + Testing Library) | DONE — 65 tests |
| Tests E2E (Playwright, desktop + Pixel 7) | DONE — 18 tests |
| CI GitHub Actions (lint, typecheck, tests back/front, build, E2E, images Docker) | BLOCKED — `.github/workflows/ci.yml` est écrit et son YAML valide (4 jobs : backend, frontend, e2e, docker), mais **le projet n'est pas un dépôt git** (`fatal: not a git repository`) et n'a pas de remote : aucune exécution n'a jamais eu lieu. `git init` + un remote GitHub suffisent à la déclencher. |
| Docker / docker-compose (Postgres, Redis, MinIO, backend, Celery, frontend) | BLOCKED — fichiers écrits et `docker-compose.yml` valide (7 services), mais **Docker n'est pas installé sur cette machine** (`docker: command not found`) : les images n'ont jamais été construites, ni ici ni en CI (voir la ligne suivante). |
| Stockage objet S3 (MinIO en local, Cloudflare R2 en prod) | PARTIALLY IMPLEMENTED — `USE_S3` bascule le storage, `prod.py` avertit s'il est désactivé, tout est documenté (STORAGE.md) ; non exercé ici contre un vrai bucket, MinIO tournant dans Docker (voir ligne précédente). |
| Déploiement réel (domaine, HTTPS, sauvegardes, supervision) | BLOCKED — procédure écrite et vérifiable (DEPLOYMENT.md), mais aucun hébergeur, domaine ni identifiant n'a été fourni : rien n'a été déployé. |

## Phase 0 — Analyse & pivot — **DONE** (2026-09-21)
- [DONE] Audit de l'existant (SSR Django, Phases 0-2 du précédent plan).
- [DONE] Décision utilisateur : pivot Next.js + DRF (voir ARCHITECTURE.md).
- [DONE] Réorganisation `nogoya/nogoya` → `backend/` + `frontend/` (Next.js).

## Phase 1 — Fondations API + Frontend — **DONE**
- [DONE] DRF + SimpleJWT (access/refresh, rotation, blacklist) + CORS +
  django-filter + drf-spectacular.
- [DONE] Endpoints auth : register, login, refresh, logout, me.
- [DONE] BFF Next.js (`/api/auth/*`) : refresh token en cookie httpOnly,
  access token en mémoire (Zustand) côté client.
- [DONE] Design system violet/blanc, thème unique contraste-audité
  (2026-09-22 — voir ARCHITECTURE.md "Design System").
- [DONE] `/healthz` et `/readyz` (DB + cache).
- [DONE] 46 tests backend verts.

## Phase 2 — Marketplace — **DONE**
- [DONE] Accueil (hero, recherche, catégories, produits récents).
- [DONE] Page recherche `/produits` (filtres catégorie/ville/type/prix,
  pagination, tri).
- [DONE] Détail produit (galerie, description, prix, badge statut,
  localisation + lien Google Maps).
- [DONE] Page fournisseur publique (`/fournisseurs/[id]`) avec catalogue
  filtrable (recherche, catégorie, prix, tri, pagination).
- [DONE] SearchEvent loggé à chaque recherche significative (anonymisé).

## Phase 3 — Comptes — **DONE (hors mot de passe oublié)**
- [DONE] Inscription (visitor/supplier), connexion, déconnexion.
- [DONE] Dashboard utilisateur (profil éditable).
- [DONE] Paramètres fournisseur (ville/adresse/bio/WhatsApp).
- [DONE] Historique de consultation + recherches récentes affichés au
  visiteur connecté (`DiscoverySections` sur `/compte`).
- [DONE] Recommandations (« pour vous », nouveautés) — moteur à règles.
- [TODO] Mot de passe oublié (OTP/e-mail) — aucun canal d'envoi provisionné.

## Phase 4 — Produits & images — **DONE**
- [DONE] CRUD produit (ownership vérifiée serveur, anti-IDOR testé).
- [DONE] Modification d'une annonce déjà publiée (slug préservé, retour en
  modération), vérifiée dans le navigateur et couverte en E2E.
- [DONE] Upload multi-images, cover automatique, compression Celery.
- [DONE] Gestion des images après publication (ajout, suppression, ordre,
  image principale) — chaque action s'applique immédiatement.
- [DONE] Éditeur d'image : recadrage (ratios 1:1, 4:3, 16:9, libre),
  rotation, miroir, zoom, rendu canvas ; `ProductImage.master` garde
  l'original pour que chaque retouche reparte de la source.
- [DONE] Attributs dynamiques par catégorie : `CategoryAttribute` (+
  héritage depuis la catégorie parente), saisie typée dans le formulaire,
  filtres de recherche (`attr_<slug>`, `_min`/`_max`), admin Django.
- [DONE] Publier/dépublier en libre-service (`is_active`).
- [DONE] Localisation + géolocalisation + précision + lien Google Maps.
- [TODO] Formulaire de création en étapes (écran unique aujourd'hui).
- [TODO] Filtres colorimétriques / détourage de fond dans l'éditeur.
- [TODO] Réorganisation d'images en drag & drop (boutons ← → aujourd'hui).

## Phase 5 — Interactions — **DONE**
- [DONE] Contact téléphone (authentifié, loggé) + WhatsApp opt-in.
- [DONE] Partage (Web Share / copie / WhatsApp) + compteur.
- [DONE] Messagerie interne complète (conversations, produit joint,
  blocage, signalement, non-lus), temps réel par polling.
- [DONE] **Messages vocaux** : enregistrement `MediaRecorder` avec
  négociation du type MIME, limites de taille et de durée, validation par
  octets magiques côté serveur, lecture inline avec durée, et **accès
  réservé aux participants** (`/messages/{id}/audio/` renvoie 403 sinon,
  redirection signée quand le stockage est S3).
- [DONE] **Favoris** : bouton sur la fiche et les cartes, page `/favoris`,
  filtre `?favorites=true`. Les cœurs se resynchronisent après hydratation
  (`/favorites/slugs/`) parce que le rendu serveur est anonyme.
- [DONE] **Notifications** : modèle générique (`Notification`), cloche avec
  compteur, page `/notifications`, filtre non-lues, tout-marquer-comme-lu.
- [TODO] WebSocket push (Channels/Redis configurés, consumer à écrire).
- [TODO] Sélecteur libre de produit à joindre côté visiteur.
- Pas de commentaires produit (exclu par le cahier des charges).

## Phase 6 — Analytics fournisseur — **DONE**
- [DONE] ProductView dédupliqué (et la dédup fonctionne réellement depuis
  que l'identifiant visiteur est stable — cf. ARCHITECTURE.md),
  SearchEvent, ContactEvent, shares_count.
- [DONE] Tuiles de stats (`GET /suppliers/me/stats/`).
- [DONE] **Graphiques** (`GET /suppliers/me/analytics/?days=`) : séries
  vues/contacts/messages, top annonces, top catégories, fenêtres 7/30/90
  jours, SVG maison (aucune librairie de charts), état vide honnête.
- [TODO] `DailyProductStats` : modèle créé, jamais peuplé (agrégation SQL
  directe pour l'instant, suffisante à cette volumétrie).

## Phase 7 — Sécurité & performance — **DONE (hors throttling général)**
- [DONE] JWT + rotation/blacklist, rafraîchissement concurrent sérialisé.
- [DONE] Permissions ownership testées (annonce, image, message, audio,
  conversation, stats, live, favoris, notifications).
- [DONE] Uploads : taille max, type MIME réel (PIL pour les images, octets
  magiques pour l'audio), durée audio bornée.
- [DONE] Identifiant visiteur validé côté serveur, jamais utilisé comme
  identité, régénéré à la déconnexion.
- [DONE] Health checks sans information sensible.
- [DONE] N+1 évités (`select_related`/`prefetch_related`), images servies
  par Next/Image, `remotePatterns` restreints.
- [DONE] Throttling : `auth` 20/min, `search` 120/min, utilisateur 600/min,
  visiteur anonyme 300/min — ce dernier compté par identifiant visiteur, le
  rendu serveur faisant arriver tout l'anonyme depuis une seule IP.

## Phase 8 — Tests — **DONE**
- [DONE] Backend : 121 tests (`python manage.py test`).
- [DONE] Frontend : 65 tests Vitest + Testing Library.
- [DONE] E2E Playwright : 18 tests, projets desktop + Pixel 7.
- [DONE] Lint, typecheck et build verts.
- Bugs réels trouvés par ces tests (et corrigés) : labels de formulaire non
  reliés à leurs champs, sessions perdues par rafraîchissement concurrent,
  CORS bloquant `/auth/me/` hors du port 3000, identifiant visiteur
  régénéré à chaque rendu, cœurs de favoris désynchronisés, tableau de
  bord affichant une annonce périmée après modification.

## Phase 9 — Production — **ÉCRIT, NON DÉPLOYÉ**
- [DONE] `Dockerfile` backend (daphne + healthcheck) et frontend
  (multi-stage, `output: "standalone"`), `docker-compose.yml` complet
  (Postgres, Redis, MinIO + création du bucket, backend, Celery, frontend).
- [DONE] Stockage objet : `USE_S3`, django-storages, MinIO en local,
  Cloudflare R2 en production (STORAGE.md).
- [ÉCRIT, JAMAIS EXÉCUTÉ] CI GitHub Actions : lint, typecheck, tests
  backend, tests frontend, build, E2E, construction des images. Le projet
  n'étant pas encore un dépôt git, le workflow n'a jamais tourné.
- [DONE] Documentation de déploiement (DEPLOYMENT.md), sécurité
  (SECURITY.md), base de données (DATABASE.md), API (API.md), stockage
  (STORAGE.md), tests (TESTING.md), live (LIVE.md).
- [BLOCKED] `docker compose build` non exécuté : Docker n'est pas installé
  sur la machine de développement, et le workflow CI qui le ferait n'a
  jamais tourné faute de dépôt git.
- [BLOCKED] Déploiement réel (domaine, HTTPS, sauvegardes, supervision) :
  aucun hébergeur ni identifiant fourni.

## Nettoyage technique en attente
- [TODO] Retirer les vues/templates SSR (`apps/*/views.py` historiques,
  `templates/`) une fois la parité fonctionnelle confirmée côté API +
  frontend (actuellement gelées, pas supprimées, pour ne rien casser).
- [TODO] Réorganisation d'images par vrai drag & drop (actuellement
  boutons ← → — fonctionnel mais moins fluide que demandé).
- [TODO] Live : l'API et les modèles existent, l'interface reste à faire
  une fois un prestataire de streaming choisi (LIVE.md décrit la couture).
- [TODO] Tâche Celery d'agrégation vers `DailyProductStats`.
