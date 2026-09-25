# Architecture — nogoya

Marketplace de location et de vente entre particuliers et professionnels
(véhicules, logements, équipements, outils, électronique, événementiel...).

## Décision majeure (2026-09-21) : pivot vers frontend découplé

Le projet a démarré (2026-09-13/14) comme une application Django monolithique
avec rendu serveur (templates + Tailwind). Le 2026-09-21, l'utilisateur a
demandé une refonte vers une marketplace généraliste multi-catégories avec
un frontend Next.js/TypeScript découplé consommant une API REST. Décision
prise après consultation de l'utilisateur (conflit avec une décision
verrouillée précédente) : **pivoter**, en conservant l'existant réutilisable.

Conservé de la version SSR :
- Modèle `User` (auth par téléphone, rôles visitor/supplier).
- Modèles `Category`, `Product`, `ProductImage`, `SupplierProfile`.
- Pipeline de compression d'image (Pillow, service + tâche Celery).
- PostgreSQL + Redis (Memurai sous Windows) + Celery, déjà opérationnels.

Retiré / remplacé :
- Les vues Django basées sur les templates (`apps/*/views.py`, `forms.py`,
  `templates/`) restent en place mais sont **gelées** : elles ne sont plus la
  surface d'interaction du produit. Elles seront supprimées une fois la parité
  fonctionnelle atteinte côté API (auth, catalogue, images) — cf. TODO.md.
  Les garder évite une régression pendant la transition (tests existants).

## Stack définitive

```
Frontend (Next.js 16, App Router, TypeScript, Tailwind v4, React 19)
    ↓ fetch (SSR direct pour les lectures publiques, Bearer JWT pour le reste)
Backend API (Django 6 + Django REST Framework, JWT via SimpleJWT)
    ↓
PostgreSQL 16 (métadonnées uniquement — aucun binaire en base)
Redis/Memurai (cache, dédup vues, broker Celery)
    ↓
Stockage objet : FileSystemStorage en dev → S3-compatible (MinIO, R2)
    ↓
CDN devant le préfixe public
```

### Frontend — `frontend/`
- Next.js 16 App Router, Server Components par défaut. Les pages qui
  affichent des données du marketplace sont `force-dynamic` (fraîcheur des
  annonces > cache statique).
- Auth : access token JWT **en mémoire** (Zustand, jamais localStorage) ;
  refresh token JWT dans un cookie **httpOnly** posé par les Route Handlers
  Next (`src/app/api/auth/*`) qui font office de BFF pour login/register/
  refresh/logout. Toutes les autres routes API (lecture publique, écriture
  authentifiée) sont appelées directement par le navigateur en Bearer auth
  (CORS activé côté Django pour l'origine du frontend).
- Design system dans `src/components/ui` (Button, Input, Select, Textarea,
  Badge, Spinner, Skeleton, EmptyState, ErrorState) — voir "Design System"
  ci-dessous.
- État serveur (listes, détail produit) : TanStack Query côté client pour
  les vues authentifiées (dashboard fournisseur) ; fetch direct + Suspense
  côté Server Components pour les pages publiques (SEO).

### Backend — `backend/`
- Apps Django : `core` (health/ready, middleware visiteur anonyme),
  `accounts` (User téléphone), `suppliers`, `catalog` (Category/Product/
  ProductImage), `analytics` (ProductView, SearchEvent, DailyProductStats),
  `api` (routeur DRF racine, monté sous `/api/v1/`).
- Auth API : SimpleJWT (access 15 min, refresh 14 jours, rotation +
  blacklist). Endpoints : `auth/register`, `auth/login`, `auth/refresh`,
  `auth/logout`, `auth/me`.
- Permissions : lecture publique (`AllowAny`) sur catalogue/fournisseurs ;
  écriture réservée au propriétaire (`IsOwnerSupplierOrReadOnly`,
  `IsImageOwnerOrReadOnly`) — jamais de confiance dans les données client
  (anti-IDOR systématique, vérifié par les tests `apps/api/tests.py`).
- Modération : `Product.status` (pending/approved/rejected, contrôlé par
  l'admin Django) + `Product.is_active` (publier/dépublier en libre-service
  par le fournisseur, sans repasser par la modération — action
  `toggle_active`). Toute modification de contenu repasse le produit en
  `pending`.
- Vues produit : dédupliquées via Redis (`apps/analytics/services.py`,
  fenêtre de 12h par utilisateur/visiteur anonyme) avant incrément
  atomique (`F()`) — évite qu'un simple refresh gonfle artificiellement
  les vues (cf. section 22 du cahier des charges).
- Visiteurs anonymes : identifiant `nogoya_vid` (UUID aléatoire, jamais
  d'IP/fingerprint). **C'est Next.js qui le pose** (`src/middleware.ts`),
  pas Django : les pages sont rendues côté serveur, donc un `Set-Cookie`
  émis par Django n'atteindrait jamais le navigateur (il meurt dans le saut
  serveur-à-serveur). Il est transmis à l'API par l'en-tête `X-Visitor-Id`,
  aussi bien par les fetch SSR (`lib/api.ts`) que par les appels navigateur
  (`lib/client-api.ts`). `apps.core.middleware.VisitorCookieMiddleware`
  valide l'en-tête (32 caractères hexadécimaux) avant de l'utiliser : c'est
  une donnée venant du client, donc uniquement une clé de regroupement
  opaque, jamais une identité. L'identifiant est **régénéré à la
  déconnexion** pour qu'un appareil partagé ne transmette pas l'historique
  d'un compte au suivant.
  *(Avant ce correctif, chaque rendu inventait un nouvel identifiant : la
  dédup de vues ne dédupliquait rien et « Vus récemment » restait
  définitivement vide.)*
- Contact fournisseur : le numéro de téléphone n'est renvoyé par l'API
  (`SupplierPublicSerializer.get_phone`) que si la requête est authentifiée
  — jamais aux visiteurs anonymes/robots.

## Design System (audit du 2026-09-22)

**Décision : thème unique violet + blanc, pas de dark-mode automatique.**
Un audit contraste a révélé que `prefers-color-scheme: dark` combiné à des
champs `bg-transparent`/sans `color-scheme` explicite pouvait laisser le
navigateur (mode sombre forcé par l'OS) réinterpréter les `<select>`/
`<option>` avec ses propres couleurs, produisant du texte invisible
(texte clair sur fond clair). Plutôt que d'auditer deux thèmes à moitié,
le thème sombre a été retiré et un seul thème — clair, violet, entièrement
spécifié — a été construit. Décision documentée ici car difficilement
réversible sans un nouvel audit complet si le dark mode revient.

- **Couleur de marque** : violet, hérité du thème de `nog-prog`
  (`#9b4dca` / `#6a0dad` / `#7a37a3`), modernisé en échelle Tailwind
  "violet" (`--brand-50` → `--brand-900`, primaire `--brand-600 = #7c3aed`).
- **Tokens** (`src/app/globals.css`) : `background`/`surface`/
  `surface-muted`/`surface-hover`, `foreground`/`foreground-muted`,
  `border`/`border-strong`, `success/warning/danger/info` (bg+fg pairs),
  `focus-ring`. Chaque composant (Button, Input/Select/Textarea, Badge,
  ErrorState) déclare explicitement background + foreground + border +
  hover + focus + disabled pour chaque variante — jamais de couleur
  héritée du navigateur ou d'une bibliothèque par défaut.
- **Fix ciblé** : `:root { color-scheme: light }` + règle globale
  `select, option, input, textarea { background-color / color: <tokens> }`
  empêche toute réinterprétation sombre des contrôles natifs.
- Ratios vérifiés manuellement pour chaque paire (texte normal ≥ 4.5:1) —
  brand-800 sur brand-50/100, foreground-muted (#5b5470) sur blanc, etc.

## Localisation & cartes (2026-09-22)

- `Product` porte `region`, `country`, `latitude`/`longitude`, `place_id`,
  `location_precision` (exact|approximate). Aucune API Google Maps payante
  n'est utilisée : `Product.map_url` génère un lien de recherche Google
  Maps (`google.com/maps/search/?api=1&query=...`) à partir des
  coordonnées ou, à défaut, de l'adresse texte — pas de clé API, pas de
  coût, pas de risque de fuite de clé.
- Géolocalisation navigateur : `navigator.geolocation.getCurrentPosition`
  côté client uniquement, jamais obligatoire (repli sur saisie manuelle).
- `location_precision=approximate` (défaut) arrondit les coordonnées
  renvoyées par l'API à 2 décimales (~1km) côté serveur
  (`Product._rounded_coordinate`) — la position exacte n'est jamais
  imposée au fournisseur.

## Contact fournisseur & WhatsApp (2026-09-22)

- Téléphone interne : révélé uniquement aux utilisateurs authentifiés,
  via l'action dédiée `POST /products/{slug}/contact/` (et non plus en
  re-fetchant le détail produit) — permet de logger un `ContactEvent`
  distinct d'une simple vue de page, utilisé pour la stat "Contacts" du
  dashboard fournisseur.
- WhatsApp : canal **opt-in** et public (`SupplierProfile.
  allow_whatsapp_contact` + `whatsapp_number`), visible même aux
  visiteurs anonymes une fois activé — volontairement moins protégé que
  le téléphone interne puisque le fournisseur choisit explicitement de
  l'exposer. Lien `wa.me/<numéro>?text=...` généré côté client, aucune
  intégration API WhatsApp payante.
- Partage : `POST /products/{slug}/share/` (anonyme, pas d'auth requise)
  incrémente `Product.shares_count`, appelé par le bouton "Partager"
  (Web Share API / copie de lien) et par le bouton WhatsApp dédié.

## Messagerie interne (2026-09-22)

- Apps `messaging` : `Conversation` (paire de participants ordonnée
  `participant_low`/`participant_high` + contrainte unique — garantit
  une seule conversation par paire d'utilisateurs, quel que soit l'ordre
  de création), `Message` (texte et/ou `shared_product` FK — un produit
  joint), `ConversationBlock`, `MessageReport`.
- API : `POST /conversations/` (démarre ou retrouve la conversation liée
  à un produit et à son fournisseur), `GET/POST /conversations/{id}/
  messages/` (paginé), `POST /conversations/{id}/read/`, `.../block/`,
  `GET /conversations/unread-count/`, `POST /message-reports/`.
- **Temps réel = polling, pas WebSocket.** Le fil se rafraîchit via
  TanStack Query (`refetchInterval` : 4 s dans un fil, 10 s pour la liste,
  15 s pour le badge non-lus). **Channels a été retiré le 2026-09-24** :
  `asgi.py` montait un routeur WebSocket avec zéro route, ce qui coûtait
  deux dépendances (`channels`, `channels-redis`) et une couche Redis
  supplémentaire pour une fonctionnalité qui n'existait pas. Le jour où le
  push se justifie, le remettre est une modification contenue : réinstaller
  les deux paquets, restaurer le `ProtocolTypeRouter` dans `asgi.py` et
  écrire le consumer. Ni le modèle de données ni l'API REST ne changent.
- **Un message porte des pièces jointes** (`media.MessageAttachment`), pas
  une colonne par type. Ajouter la vidéo à la manière précédente aurait
  signifié `video_file`, `video_duration`, `video_poster`, `video_width`…
  et un sérialiseur qui gagne une branche par format. Les vocaux existants
  ont été migrés vers ce modèle (migration `0003_move_audio_to_attachments`,
  sans copier les octets : la ligne pointe sur la clé déjà occupée).
- Frontend : `/compte/messages` (liste), `/compte/messages/[id]` (fil).
  Le bouton "Envoyer un message" sur la fiche produit
  (`ContactSupplierCard`) démarre la conversation. Un fournisseur peut
  joindre une de ses propres annonces via le bouton "+" ; un visiteur
  peut joindre le produit d'origine de la conversation via un raccourci
  dédié (pas encore de sélecteur libre parmi tout le catalogue du
  fournisseur — limitation connue, cf. TODO.md).
- **Recherche** : `SearchFilter` DRF (titre/description/ville) + filtres
  structurés (catégorie, ville, type, prix). Pas d'Elasticsearch pour le
  MVP ; migration possible vers Postgres trigram/full-text puis un moteur
  dédié si le volume l'exige (section 50 du cahier des charges).
- **Catégories** : arbre à 2 niveaux (parent/enfant) via FK `self` sur
  `Category`. Pas encore d'attributs dynamiques par catégorie (ex.
  marque/année pour un véhicule) — prévu en V2, cf. TODO.md ; le modèle
  `Category` n'empêche pas cette extension (pas de champs figés sur
  `Product`).
- **Pas de commentaires produit.** Décision produit explicite (2026-09-22) :
  aucune UI ni endpoint de commentaire public sur les annonces. Les
  statistiques fournisseur reposent sur vues/contacts/partages, pas sur
  des commentaires.
- **Live** : modèles et API livrés le 2026-09-23 (`apps/live`), sans
  infrastructure vidéo — les champs `provider`/`playback_url`/`ingest_url`
  sont les coutures prévues. Voir LIVE.md.

## Attributs dynamiques par catégorie (2026-09-23)

`Product` ne porte **aucun** champ spécifique à une catégorie. Trois modèles
suffisent : `Category` → `CategoryAttribute` (déclaration) →
`ProductAttributeValue` (valeur). Ajouter « nombre de chambres » aux
logements se fait dans l'admin, sans migration ni déploiement.

- `ProductAttributeValue.value` est un `JSONField` : une seule colonne pour
  texte, nombre, booléen, date et multi-choix. `numeric_value` est
  dénormalisé à l'enregistrement pour que les filtres par plage restent
  indexables (index `(attribute, numeric_value)`).
- Une sous-catégorie **hérite** des attributs de son parent
  (`Category.effective_attributes()`) : « kilométrage » est déclaré une fois
  sur Véhicules et vaut pour Voitures, Motos et Utilitaires.
- Seuls les attributs marqués `filterable` sont exploitables comme filtre
  public (`?attr_<slug>=`, `?attr_<slug>_min/_max=`) : un fournisseur ne
  peut pas transformer un champ interne en facette de recherche.
- Le formulaire frontend est entièrement piloté par les données renvoyées
  par `/categories/` — aucun champ n'est codé en dur côté client.

## Chat multimédia (2026-09-24)

Le chat transporte texte, vocaux, images, vidéos et annonces. Tout ce qui
est fichier passe par `media.MessageAttachment` et par le même pipeline.

- **Enregistrement vocal** par l'API native `MediaRecorder`, sans service
  externe. Le format n'est jamais supposé : `pickRecordingMimeType()`
  demande au navigateur ce qu'il sait produire (WebM/Opus sur
  Chrome/Firefox/Edge, MP4/AAC sur Safari, Ogg en repli). Mono, débit
  modeste : une voix claire dans un petit fichier.
- **Images** : réduites dans le navigateur (canvas) avant l'envoi, puis
  re-encodées côté serveur en trois rendus. Voir STORAGE.md.
- **Vidéos** : durée, dimensions et image d'aperçu extraites par le
  navigateur ; pas de transcodage serveur (décision et couture documentées
  dans STORAGE.md).
- **Validation serveur** : taille, durée, MIME en liste blanche **et**
  octets d'en-tête réels (EBML, OggS, ftyp…). Un fichier HTML renommé
  `.webm` est rejeté, quel que soit son `Content-Type`.
- **Diffusion** : jamais d'URL de stockage. L'API revérifie l'appartenance à
  la conversation puis **streame les octets**, quel que soit le backend. Le
  navigateur les récupère par un `fetch` authentifié converti en object
  URL : une balise `<img src>` ou `<audio src>` n'enverrait pas le jeton.
  Le détail (et pourquoi l'« URL signée » précédente n'en était pas une) est
  dans SECURITY.md.
- **Coût d'affichage** : une bulle ne charge que la vignette, et seulement
  quand elle approche de l'écran (`IntersectionObserver`). Une vidéo ne
  télécharge que son poster tant que personne n'appuie sur lecture. Remonter
  une longue conversation ne doit pas rapatrier tous les clips jamais
  envoyés.
- **Envoi** : `XMLHttpRequest` et non `fetch`, uniquement parce que `fetch`
  n'expose aucune progression d'upload — quelqu'un qui envoie 40 Mo sur une
  connexion lente doit voir où il en est, et pouvoir annuler.

## Graphiques du dashboard (2026-09-23)

Les graphiques sont des **SVG écrits à la main** (`components/charts/`),
sans bibliothèque. Un `LineChart` responsive et un `BarList` accessible
représentent environ 150 lignes — nettement moins lourd qu'une dépendance
de graphiques, et les couleurs viennent directement des tokens violet du
design system. Quand une série est vide, l'interface affiche « Pas encore
assez de données » plutôt qu'un cadre vide.

Les séries sont agrégées **en SQL** (`TruncDate` + `Count`), une requête
par série, puis complétées côté Python pour avoir un point par jour (zéros
inclus) — jamais de boucle de requêtes par jour.

## Rendu serveur et état propre à l'utilisateur (2026-09-23)

Les pages publiques sont rendues côté serveur et **ce fetch est anonyme** :
le token d'accès vit en mémoire dans le navigateur, il n'existe pas au
moment du rendu. Tout ce qui dépend de la personne connectée doit donc être
réconcilié après hydratation, jamais lu dans le HTML initial.

- **Favoris** : `is_favorite` vaut toujours `false` dans le HTML. Le
  navigateur appelle `GET /favorites/slugs/` une fois et corrige tous les
  cœurs affichés. Sans cela, une annonce déjà enregistrée s'affichait avec
  un cœur vide — et le clic suivant la *retirait* des favoris au lieu de
  l'ajouter (bug trouvé par la suite E2E).
- **Téléphone du fournisseur** : jamais dans le HTML non plus, récupéré à
  la demande par `POST /products/{slug}/contact/` (et journalisé).
- **Identifiant visiteur** : posé par le middleware Next.js et transmis par
  l'en-tête `X-Visitor-Id` (voir plus haut).

Règle : si une donnée dépend de `request.user`, elle passe par
`client-api.ts`, pas par `server-api.ts`.

## Recommandations (2026-09-23)

Moteur **à règles**, pas de ML : historique de consultation + catégories
favorites + ville, avec repli sur les annonces les plus vues pour un
visiteur inconnu. Fonctionne dès le premier jour sur un petit jeu de
données. `apps/analytics/recommendations.py` est la seule couture à
remplacer le jour où un moteur plus avancé se justifie.

Les visiteurs anonymes sont servis via `nogoya_vid` : la découverte ne
nécessite pas de compte. Un visiteur **connecté** voit aussi l'historique
rattaché à l'identifiant de son navigateur (`Q(user=…) | Q(visitor_id=…)`),
puisque le rendu serveur enregistre les vues sans utilisateur — sans cela,
« Vus récemment » restait vide précisément pour les gens connectés.

## Stockage objet (2026-09-23)

`USE_S3` bascule le storage par défaut entre `FileSystemStorage` et
`S3Storage` (django-storages). Aucun code applicatif ne teste ce drapeau :
les `ImageField`/`FileField` utilisent simplement le storage par défaut.
MinIO en local, Cloudflare R2 en production. Voir STORAGE.md.

`ProductImage.master` conserve l'upload d'origine : chaque recadrage repart
de l'original au lieu de dégrader une image déjà recompressée.

## Coûts (cible MVP)

- Frontend : Vercel (ou Cloudflare Pages) — gratuit au démarrage.
- Backend : Railway/Render/VPS économique (Django + Postgres + Redis).
- Médias : Cloudflare R2 (S3-compatible, pas de frais de sortie) —
  **câblé** depuis le 2026-09-23 via django-storages ; MinIO joue le même
  rôle en local (`docker compose`).
- Redis : Memurai en local (Windows) ; Upstash/Redis managé en prod (plan
  gratuit suffisant au MVP).

## Structure du dépôt

```
DEVELOPPEMENT/nogoya/
├── backend/          Django + DRF (voir backend/README.md)
├── frontend/          Next.js (voir frontend/.env.example)
├── ARCHITECTURE.md    ce fichier
├── PRODUCT_SPEC.md    périmètre produit détaillé
├── TODO.md            suivi des phases
└── nog-prog/          ANCIEN projet — ne jamais modifier
```
