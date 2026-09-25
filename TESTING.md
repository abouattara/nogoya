# Tests — nogoya

Trois niveaux : tests backend (Django, **121 tests**), tests de composants
(Vitest, **65 tests**) et parcours end-to-end (Playwright, **18 tests** sur
deux projets : desktop et Pixel 7).

## Backend — Django

```bash
cd backend
.\.venv\Scripts\Activate.ps1
python manage.py test              # toute la suite
python manage.py test apps.catalog # une app
```

Les tests tournent contre **PostgreSQL et Redis réels** (pas de mock) :
c'est volontaire, la déduplication des vues repose sur le cache Redis et les
agrégats de statistiques sur des fonctions SQL PostgreSQL. Les deux services
doivent tourner.

Couverture par app :

| App | Ce qui est testé |
|---|---|
| `accounts` | inscription, connexion, rôles, permissions |
| `catalog` | CRUD annonce, anti-IDOR, upload d'images, favoris, attributs dynamiques et leurs filtres |
| `messaging` | conversations, permissions, blocage/signalement, pièces jointes (images, vidéos, vocaux : validation, compression, ordre, accès, notifications) |
| `media` | pipeline d'images (rendus, EXIF, orientation), suppression des fichiers, balayage des orphelins |
| `notifications` | isolation par utilisateur, compteur non-lus, tout marquer comme lu |
| `live` | création, permissions hôte, produits épinglés, spectateurs, chat |
| `analytics` | séries temporelles du dashboard, recommandations, isolation des données |
| `api` | auth JWT, contact/partage, statistiques fournisseur |

## Frontend — Vitest + Testing Library

```bash
cd frontend
npm test            # une fois
npm run test:watch  # en continu
```

Configuration : `vitest.config.mts` (jsdom) et `vitest.setup.tsx`, qui
stubbe `next/navigation`, `next/image` et les APIs média absentes de jsdom.

Composants couverts : `ProductCard`, `FavoriteButton`, `AudioMessage`,
`AudioRecorder`, `DynamicAttributeFields`, `NotificationBell`, `LineChart`,
`BarList`, `ProductForm`, `AuthProvider`, l'identifiant visiteur
(`lib/visitor.ts`) et les primitives du design system
(`Input`/`Select`/`Textarea`/`Badge`/`EmptyState`/`ErrorState`).

Les tests d'`AudioRecorder` fournissent un faux `MediaRecorder` : jsdom n'en
a pas, et on veut vérifier le cycle enregistrer → pause → arrêt →
prévisualisation → envoi sans micro réel.

## E2E — Playwright

Prérequis : **le backend Django doit tourner** et la base contenir les
données de démo. Playwright démarre lui-même le frontend.

```bash
# terminal 1
cd backend
python manage.py runserver 127.0.0.1:8000   # les données de démo sont
                                            # (re)semées par global-setup

# terminal 2
cd frontend
npm run test:e2e       # construit le frontend puis lance la suite
npm run test:e2e:ui    # mode interactif
```

Playwright reconstruit le frontend lui-même avant de démarrer le serveur :
lancer la suite sur un `.next` périmé testerait silencieusement du code
obsolète (c'est arrivé pendant le développement).

Comptes utilisés (créés par `seed_demo`, mot de passe `DemoPass123!`) :
fournisseurs `+22670010001` / `+22670010002`, visiteur `+22670020001`.

Parcours couverts :

| Fichier | Parcours |
|---|---|
| `e2e/visitor.spec.ts` | accueil → recherche → filtres (dont caractéristiques) → produit → fournisseur, états vides, favori qui redirige vers la connexion |
| `e2e/user.spec.ts` | favoris, chat (texte, photo, refus d'un fichier trop lourd), bouton micro, notifications, suggestions du tableau de bord |
| `e2e/supplier.spec.ts` | création d'annonce avec attributs et image, modification d'une annonce publiée, retouche d'une image publiée, statistiques, publier/dépublier, live (API) |
| `e2e/mobile.spec.ts` | menu mobile, absence de débordement horizontal, accès favoris/notifications (projet Pixel 7) |

La suite tourne avec `workers: 1` : elle partage une base de données
commune, et l'exécution parallèle produirait des interférences entre
parcours (favoris, conversations). Pour la même raison, **ne pas lancer
deux exécutions en parallèle** : la seconde tue le serveur web de la
première (`ERR_CONNECTION_REFUSED`).

La suite modifie les données : les annonces qu'elle édite repassent en
modération et chaque exécution ajoute une annonce « Berline E2E … ». Pour
que le jeu de données reparte propre, `e2e/global-setup.ts` relance
`seed_demo` (qui remet ses propres annonces en ligne) et supprime les
annonces « Berline E2E » des exécutions précédentes, avant chaque suite.
`E2E_SKIP_SEED=1` désactive cette étape.

Les tests qui lisent le tableau de bord fournisseur doivent **attendre**
son rendu : il est chargé côté client. Le test « publier / dépublier »
comptait ses boutons juste après `goto()`, n'en trouvait aucun et se
mettait en *skip* — à chaque exécution, y compris sur des données
fraîchement semées. Un test qui se saute n'est pas un test qui passe : la
suite n'a plus aucun *skip*, et si elle en affiche un, c'est un signal, pas
du bruit.

Le backend doit accepter l'origine du serveur de test
(`http://127.0.0.1:3100`) : `config/settings/dev.py` autorise tous les
ports locaux via `CORS_ALLOWED_ORIGIN_REGEXES`. Une origine figée sur le
port 3000 faisait échouer `/auth/me/` en `net::ERR_FAILED`, et tous les
parcours connectés avec.

## Vérification complète avant livraison

```bash
cd backend  && python manage.py check && python manage.py makemigrations --check --dry-run && python manage.py test
cd frontend && npm run lint && npm run typecheck && npm test && npm run build && npm run test:e2e
docker compose build
```

## Bugs réels trouvés par ces tests

Ils sont listés ici parce qu'ils justifient le coût de la suite — aucun
n'avait été repéré à la lecture du code :

| Trouvé par | Bug |
|---|---|
| Vitest (`ProductForm`) | labels non reliés à leurs champs : formulaires inutilisables au lecteur d'écran, dans toute l'application |
| E2E (parcours connectés) | CORS limité au port 3000 : session perdue dès que le frontend écoutait ailleurs |
| E2E + Vitest (`AuthProvider`) | rafraîchissements concurrents du token : le second échouait et déconnectait la personne |
| E2E (favoris) | cœur toujours vide au chargement (rendu serveur anonyme) : recliquer *retirait* le favori |
| E2E (fournisseur) | tableau de bord affichant l'ancien titre après modification (cache TanStack Query de 30 s) |
| Vérification manuelle (compteur de vues) | identifiant visiteur régénéré à chaque rendu : dédup des vues inopérante, « Vus récemment » toujours vide |
| Relecture du code de stockage | la « URL signée » des vocaux ne signait rien (`AWS_QUERYSTRING_AUTH = False`) et le bucket était public en entier : un vocal privé était lisible par toute personne ayant le lien |
| Relecture du lecteur audio | `<audio src="/api/…">` part sans en-tête `Authorization` : écouter un vocal renvoyait 401 (« Vocal indisponible ») |
| Vérification dans le navigateur | une fois l'authentification corrigée, l'endpoint répondait **406** : DRF négocie le renderer sur l'en-tête `Accept` avant d'exécuter la vue |
| Relecture du code de limitation de débit | le quota `search` était déclaré dans les réglages mais appliqué à aucune vue ; et compté par IP, il aurait été partagé par tout le site, le rendu serveur masquant l'adresse réelle |
| Vérification manuelle (login) | une erreur JSON brute (« Unexpected end of JSON input ») s'affichait dans le formulaire de connexion quand l'API redémarrait |
| Relecture du test « publier / dépublier » | il comptait les boutons avant que le tableau (chargé côté client) n'existe : il se mettait donc en *skip* à chaque exécution au lieu de tester quoi que ce soit |
| Vitest (`AttachmentGallery`) | une vidéo ne se chargeait jamais au clic sur « lire » : `useState(eager)` ne lit sa valeur qu'au premier rendu, donc le passage de `eager` à `true` ne débloquait rien |
| Tests backend (pièces jointes) | les dimensions enregistrées étaient celles du master alors que le fichier stocké est le rendu d'affichage : l'interface aurait réservé la mauvaise place et chaque image aurait sauté au chargement |
| `prune_media` (relecture avant exécution) | la première version listait les champs fichiers à la main et ignorait `User.avatar` et `LiveSession.thumbnail` : elle aurait supprimé des fichiers vivants. Elle les découvre désormais par introspection |
