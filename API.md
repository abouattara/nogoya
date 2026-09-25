# API — nogoya

Base : `/api/v1/`. Documentation interactive générée par drf-spectacular :
`/api/v1/docs/` (schéma OpenAPI brut : `/api/v1/schema/`).

Authentification : `Authorization: Bearer <access token>`.
Pagination : `?page=N` (20 éléments par page), réponse
`{count, next, previous, results}`.

## Authentification

| Méthode | Endpoint | Description |
|---|---|---|
| POST | `/auth/register/` | inscription (`phone`, `first_name`, `last_name`, `role`, `password`, `password2`) |
| POST | `/auth/login/` | renvoie `access`, `refresh` et un résumé `user` |
| POST | `/auth/refresh/` | échange un refresh token (rotation + blacklist) |
| POST | `/auth/logout/` | blackliste le refresh token |
| GET/PATCH | `/auth/me/` | profil courant (`phone` et `role` en lecture seule) |

Côté frontend, ces quatre routes passent par le BFF Next.js
(`/api/auth/*`) qui garde le refresh token dans un cookie `httpOnly`.

## Catalogue

| Méthode | Endpoint | Description |
|---|---|---|
| GET | `/categories/` | arbre des catégories, **avec leurs attributs** (hérités du parent inclus) |
| GET | `/products/` | recherche publique |
| POST | `/products/` | création (fournisseur) |
| GET | `/products/{slug}/` | détail (incrémente les vues, dédupliquées 12 h) |
| PATCH | `/products/{slug}/` | modification (propriétaire) — repasse en modération |
| DELETE | `/products/{slug}/` | suppression (propriétaire) |
| POST | `/products/{slug}/upload_images/` | upload multipart (`images`, multiple) |
| POST | `/products/{slug}/toggle_active/` | publier / dépublier une annonce approuvée |
| POST | `/products/{slug}/toggle_favorite/` | ajouter / retirer des favoris |
| POST | `/products/{slug}/contact/` | révèle le contact et journalise (`channel`: `phone`\|`whatsapp`) |
| POST | `/products/{slug}/share/` | incrémente le compteur de partages (anonyme) |
| PATCH/DELETE | `/product-images/{id}/` | réordonner, choisir la principale, supprimer |
| POST | `/product-images/{id}/replace/` | remplace le rendu (éditeur crop/rotation), `master` conservé |
| GET/DELETE | `/favorites/` , `/favorites/{id}/` | favoris de l'utilisateur courant |
| GET | `/favorites/slugs/` | les slugs favoris, pour resynchroniser les cœurs après hydratation (le rendu serveur est anonyme) |

### Filtres de `/products/`

```
?search=tente               texte (titre, description, ville)
&category=voitures          slug de catégorie
&city=Ouagadougou
&listing_type=rent|sale
&price_min=1000&price_max=50000
&supplier=3                 id de SupplierProfile
&favorites=true             uniquement mes favoris
&mine=true                  mes annonces (tous statuts)
&ordering=price|-price|-created_at|-views_count
```

**Filtres par attribut dynamique** — uniquement les attributs marqués
`filterable` :

```
?attr_carburant=Diesel      select / texte / booléen (true|false)
&attr_annee_min=2018        borne basse (attribut numérique)
&attr_annee_max=2022        borne haute
```

### Création / modification avec attributs

```json
POST /api/v1/products/
{
  "title": "Berline 2019",
  "category": 12,
  "description": "...",
  "price": 4500000,
  "listing_type": "sale",
  "city": "Ouagadougou",
  "location_precision": "approximate",
  "attributes": { "marque": "Toyota", "annee": 2019, "carburant": "Diesel" }
}
```

Les erreurs d'attribut reviennent champ par champ :
`{"attributes": {"marque": "« Marque » est obligatoire."}}`.

## Messagerie

| Méthode | Endpoint | Description |
|---|---|---|
| GET | `/conversations/` | liste (dernier message, non-lus, produit d'origine) |
| POST | `/conversations/` | démarre ou retrouve la conversation liée à `{"product": id}` |
| GET | `/conversations/{id}/messages/` | fil paginé |
| POST | `/conversations/{id}/messages/` | envoi (multipart) : `body`, `shared_product`, `images[]`, `videos[]`, `audios[]`, `posters[]`, `durations[]` |
| GET | `/conversations/{id}/messages/{mid}/attachments/{aid}/` | le fichier (participants uniquement) |
| GET | `/conversations/{id}/messages/{mid}/attachments/{aid}/poster/` | la vignette / image d'aperçu |
| POST | `/conversations/{id}/read/` | marque comme lus |
| POST | `/conversations/{id}/block/` | bloque la conversation |
| GET | `/conversations/unread-count/` | compteur global |
| POST | `/message-reports/` | signale un message (`message`, `reason`) |

Un message porte un tableau `attachments` :

```json
{
  "id": 25, "message_type": "image", "body": "Voici l'article",
  "attachments": [{
    "id": 4, "kind": "image", "status": "ready",
    "url": ".../attachments/4/", "poster_url": ".../attachments/4/poster/",
    "mime_type": "image/jpeg", "size": 12293,
    "width": 900, "height": 600, "duration": 0
  }]
}
```

`kind` vaut `image`, `video` ou `audio` ; `status` vaut `uploading`,
`processing`, `ready` ou `failed`. `message_type` nomme le message d'après
ce qu'il transporte, média d'abord : une photo légendée se lit « Photo »
dans la liste des conversations.

`durations` et `posters` sont appariés **par ordre** avec `videos` puis
`audios`. Une vidéo sans poster exploitable part quand même, avec un
placeholder.

Les fichiers ne sont jamais servis par une URL de stockage : une
conversation est privée, et un lien de bucket resterait lisible par
quiconque l'obtient. L'appartenance est revérifiée à chaque requête.

Temps réel : polling côté client (4 s dans un fil, 10 s pour la liste,
15 s pour les compteurs). Channels a été retiré : router des WebSockets sans
aucun consumer coûtait deux dépendances et une couche Redis pour rien (voir
ARCHITECTURE.md).

## Notifications

| Méthode | Endpoint | Description |
|---|---|---|
| GET | `/notifications/` | les siennes (`?unread=true` pour filtrer) |
| GET | `/notifications/unread-count/` | compteur |
| POST | `/notifications/{id}/read/` | marque une notification comme lue |
| POST | `/notifications/read-all/` | marque tout comme lu |
| DELETE | `/notifications/{id}/` | supprime |

Types : `new_message`, `new_product`, `product_updated`,
`product_approved`, `product_rejected`, `favorite`, `live_started`,
`system`. Le champ `url` porte le chemin frontend à ouvrir au clic.

## Fournisseurs

| Méthode | Endpoint | Description |
|---|---|---|
| GET | `/suppliers/` , `/suppliers/{id}/` | profil public + catalogue |
| GET/PATCH | `/suppliers/me/` | son propre profil (ville, bio, WhatsApp) |
| GET | `/suppliers/me/stats/` | tuiles : annonces en ligne, vues, contacts, messages non lus |
| GET | `/suppliers/me/analytics/?days=30` | séries temporelles + top annonces/catégories |

`days` est borné entre 7 et 365 (30 par défaut).

## Découverte

| Méthode | Endpoint | Description |
|---|---|---|
| GET | `/discovery/me/` | vus récemment, recommandations, nouveautés, recherches récentes |

Fonctionne aussi pour un visiteur anonyme, via l'en-tête `X-Visitor-Id`
(identifiant opaque posé par le frontend, validé côté API — voir
SECURITY.md). Tout endpoint qui enregistre de l'analytics (`GET
/products/`, `GET /products/{slug}/`) accepte le même en-tête ; sans lui,
chaque appel compte comme un visiteur inédit.

## Live

| Méthode | Endpoint | Description |
|---|---|---|
| GET/POST | `/lives/` | liste publique (hors brouillons) / création (la réponse renvoie la session complète, pas seulement les champs écrits) |
| POST | `/lives/{id}/start/` , `/end/` | hôte uniquement |
| POST | `/lives/{id}/join/` , `/leave/` | présence spectateur |
| GET/POST | `/lives/{id}/products/` | annonces présentées |
| POST | `/lives/{id}/products/{product}/pin/` , `/unpin/` | mise en avant |
| GET/POST | `/lives/{id}/messages/` | chat du live |

Détails dans LIVE.md.

## Santé

| Endpoint | Description |
|---|---|
| `/healthz/` | liveness |
| `/readyz/` | readiness (PostgreSQL + cache), 503 si dégradé |

## Codes de retour

| Code | Signification |
|---|---|
| 400 | validation — corps `{champ: [messages]}` |
| 401 | absent ou expiré : rafraîchir l'access token |
| 403 | authentifié mais non autorisé (ex. non-fournisseur) |
| 404 | inexistant **ou** hors de votre périmètre (jamais de fuite d'existence) |
| 429 | quota dépassé : 20/min sur connexion et inscription, 120/min sur `GET /products/`, 600/min par utilisateur connecté, 300/min par visiteur anonyme (compté par identifiant visiteur, pas par IP — cf. SECURITY.md) |
