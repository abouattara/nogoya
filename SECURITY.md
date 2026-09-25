# Sécurité — nogoya

## Authentification

- Identifiant de connexion : **numéro de téléphone** (`USERNAME_FIELD`),
  mots de passe hachés par Django (PBKDF2), validateurs actifs (longueur
  minimale 8, similarité avec le profil, mots de passe courants, tout
  numérique).
- JWT via SimpleJWT : access 15 min, refresh 14 jours, **rotation** des
  refresh tokens et **blacklist** du précédent à chaque rotation.
- Le refresh token n'est jamais accessible au JavaScript : il est stocké
  dans un cookie `httpOnly` posé par les Route Handlers Next.js
  (`/api/auth/*`), qui font office de BFF. Le navigateur ne manipule que
  l'access token, gardé **en mémoire** (jamais `localStorage`), ce qui
  limite la fenêtre d'exploitation d'une XSS.
- Déconnexion : le refresh token est blacklisté côté serveur et le cookie
  supprimé.
- Rate limiting : `20/min` sur l'inscription et la connexion
  (`ScopedRateThrottle`, scope `auth`) pour ralentir le bourrage
  d'identifiants.

## Autorisations — règle générale

Chaque ressource est filtrée par propriétaire **au niveau du queryset**, pas
seulement par une vérification de permission. Un identifiant deviné renvoie
donc 404, sans révéler l'existence de l'objet.

| Ressource | Règle |
|---|---|
| Annonce | modification/suppression réservées au fournisseur propriétaire (`IsOwnerSupplierOrReadOnly`) ; une annonce non approuvée ou dépubliée est en 404 pour tout autre visiteur |
| Images | même propriétaire que l'annonce (`IsImageOwnerOrReadOnly`), y compris pour `replace/` |
| Favoris | `Favorite.objects.filter(user=request.user)` — supprimer le favori d'autrui donne 404 |
| Notifications | idem : jamais celles d'un autre compte, y compris pour « marquer comme lu » |
| Conversations | accès réservé aux deux participants (`IsConversationParticipant`) |
| Vocaux | servis par une vue qui recharge la conversation et vérifie l'appartenance, puis **streame les octets** — jamais de redirection vers le stockage, quel que soit le backend (voir ci-dessous) |
| Live | modification, démarrage, arrêt et épinglage réservés à l'hôte ; un hôte ne peut présenter que **ses propres** annonces |
| Statistiques | un fournisseur ne voit que ses propres données (filtrage sur `supplier=profile`) |
| Attributs de catégorie | configuration réservée à l'administration ; seuls les attributs marqués `filterable` sont exploitables comme filtre public |

Ces règles sont couvertes par des tests explicites (« un tiers ne peut
pas… »), pas seulement par le code.

## Uploads

Le `Content-Type` envoyé par le navigateur n'est jamais cru sur parole.

**Images** (`apps/catalog/validators.py`) : taille max (10 Mo par défaut),
type MIME dans une liste blanche, extension contrôlée, puis décodage réel
par Pillow (`verify()`) et vérification du format détecté. La validation
porte sur **tous** les fichiers d'un lot avant le moindre enregistrement :
un fichier corrompu ne laisse pas une galerie à moitié créée.

**Audio** (`apps/messaging/validators.py`) : taille max, durée max (300 s),
MIME en liste blanche et surtout contrôle des **octets d'en-tête** (EBML
pour WebM, `OggS`, `ftyp` pour MP4/M4A, ID3/ADTS…). Un fichier HTML
renommé `.webm` avec le bon `Content-Type` est rejeté.

### Vocaux : pourquoi l'API sert les octets elle-même

Le code redirigeait auparavant vers `storage.url(name, expire=300)` en
croyant produire une URL signée. C'était faux : `AWS_QUERYSTRING_AUTH =
False` — indispensable pour servir les images d'annonces publiquement —
désactive la signature, `expire` est ignoré et l'URL renvoyée reste valable
tant que l'objet existe. Le vocal d'une conversation privée devenait donc
lisible par quiconque obtenait ce lien.

Deux verrous depuis :

1. l'API **streame** le fichier après vérification d'appartenance, avec
   `Cache-Control: private, no-store` — aucune URL de stockage ne sort ;
2. l'accès anonyme au bucket est restreint au préfixe `products/`
   (images d'annonces). `messages/audio/` reste privé, donc même un chemin
   deviné ne donne rien. Voir STORAGE.md.

Le client joue le vocal via un `fetch` authentifié converti en object URL :
une balise `<audio src="/api/…">` émet une requête *sans* en-tête
`Authorization` (le token ne vit qu'en mémoire) et recevait un 401.

## Protections web

- **CORS** restreint aux origines déclarées (`CORS_ALLOWED_ORIGINS`), jamais
  `*`.
- **CSRF** : `CsrfViewMiddleware` actif, `CSRF_TRUSTED_ORIGINS` configuré ;
  l'API est consommée en Bearer (pas de cookie de session), donc non exposée
  au CSRF, et le cookie de refresh est en `SameSite=Lax`.
- **XSS** : React échappe par défaut ; aucun `dangerouslySetInnerHTML` dans
  le code.
- **Injection SQL** : exclusivement l'ORM Django, aucune requête SQL
  concaténée.
- **Clickjacking** : `X_FRAME_OPTIONS=DENY`.
- **HSTS** un an, `SECURE_CONTENT_TYPE_NOSNIFF`, cookies `Secure` et
  `HttpOnly` en production.

### Limitation de débit

| Portée | Limite | Pourquoi |
|---|---|---|
| `auth` (connexion, inscription) | 20/min | bourrage d'identifiants |
| `search` (`GET /products/`) | 120/min | aspiration du catalogue |
| utilisateur connecté | 600/min | garde-fou, jamais atteint en usage normal |
| visiteur anonyme | 300/min | idem, **par navigateur** |

L'anonyme n'est **pas** limité par adresse IP : les pages sont rendues côté
serveur, donc toutes les requêtes anonymes arrivent avec l'adresse du
serveur Next.js — une limite par IP aurait bloqué le site entier dès qu'un
visiteur dépasse le seuil. `apps/core/throttling.py` compte par identifiant
visiteur, pour les limites globales (`VisitorRateThrottle`) comme pour les
limites par portée (`VisitorScopedRateThrottle`).

C'est particulièrement vrai pour `auth` : la connexion passe par la route
BFF de Next.js, donc **toutes** les tentatives du site arrivent de la même
adresse. Avec une clé par IP, 20 tentatives par minute auraient été le
budget du site entier : pénible pour les utilisateurs, et inutile face à un
attaquant, qui n'aurait eu qu'à épuiser le quota pour bloquer tout le monde.
Les routes `/api/auth/login` et `/api/auth/register` transmettent donc
`X-Visitor-Id`.

Un identifiant visiteur étant fourni par le client, le faire tourner
contourne la limite — exactement comme changer d'IP contourne une limite par
IP. C'est un garde-fou contre l'abus ordinaire, pas contre un attaquant
déterminé : ce dernier se traite au bord du réseau (Cloudflare), cf.
DEPLOYMENT.md.

Un refus (429) remonte à l'utilisateur en français (« Trop de tentatives.
Patientez une minute… »), jamais comme une erreur technique brute.

## Vie privée

- Le **numéro de téléphone** d'un fournisseur n'est jamais renvoyé à un
  visiteur anonyme. Il n'est révélé qu'à un utilisateur connecté, via une
  action dédiée (`POST /products/{slug}/contact/`) qui journalise
  l'intention de contact.
- Le **numéro WhatsApp** est un canal *opt-in* : visible publiquement
  seulement si le fournisseur l'a activé explicitement.
- La **position exacte** d'une annonce n'est jamais imposée : par défaut la
  précision est « approximative » et les coordonnées renvoyées par l'API
  sont arrondies à ~1 km côté serveur.
- Les **visiteurs anonymes** sont suivis par un identifiant `nogoya_vid`
  contenant un UUID aléatoire — jamais d'IP ni d'empreinte navigateur. Il
  sert à dédupliquer les vues et à personnaliser la découverte.
  - Le cookie est posé par le middleware Next.js sur notre domaine et
    transmis à l'API via l'en-tête `X-Visitor-Id`. Il est lisible par le
    JavaScript de la page (les appels navigateur doivent l'envoyer) : c'est
    assumé, la valeur est un identifiant opaque sans donnée personnelle.
  - L'en-tête est **validé** côté Django (`^[0-9a-f]{32}$`) et rejeté
    sinon : il vient du client, donc il ne sert qu'à regrouper des lignes
    d'analytics, jamais à authentifier ni à autoriser quoi que ce soit.
    Forger un identifiant ne donne accès à rien — les données personnelles
    restent filtrées par `request.user`.
  - Il est **régénéré à la déconnexion** : sur un appareil partagé, la
    personne suivante ne récupère pas l'historique de navigation du compte
    précédent dans ses suggestions.
- Les vues d'annonce sont dédupliquées (12 h par visiteur) : le compteur
  affiché n'est pas gonflable par simple rechargement.

## Secrets

Aucun secret dans le dépôt. Tout passe par variables d'environnement
(`django-environ`), avec `.env.example` comme documentation et `.env`
ignoré par Git et Docker. En production, `DJANGO_SECRET_KEY` et
`DJANGO_ALLOWED_HOSTS` n'ont pas de valeur par défaut : l'application
refuse de démarrer si elles manquent.

## Points connus à traiter

- Pas encore de vérification du numéro de téléphone (OTP) ni de
  récupération de mot de passe.
- Modération : approbation manuelle en back-office, sans détection
  automatique de contenu illicite.
