# Base de données — nogoya

PostgreSQL 16. Toutes les tables sont gérées par l'ORM Django ; aucune
migration écrite à la main.

## Schéma

### Comptes

```
User (accounts)
  phone (unique, identifiant de connexion)  role: supplier | visitor
  first_name, last_name, email, gender, birth_date, avatar
  is_phone_verified, created_at

SupplierProfile (suppliers)     1-1 User
  city, address, bio, is_verified, rating_avg
  whatsapp_number, allow_whatsapp_contact   ← canal opt-in
```

### Catalogue

```
Category (catalog)              arbre à 2 niveaux (parent → self)
  name, slug, icon, order

CategoryAttribute (catalog)     attributs déclarés par catégorie
  category, name, slug, attribute_type, required,
  filterable, searchable, unit, options (JSON), position
  unique(category, slug)

Product (catalog)
  supplier, category, title, slug (unique, stable),
  description, price, currency, listing_type (rent|sale), rental_period,
  status (pending|approved|rejected), is_active,
  city, location, region, country, latitude, longitude, place_id,
  location_precision (exact|approximate),
  views_count, shares_count, published_at, created_at, updated_at

ProductImage (catalog)
  product, image, master (original intact), is_cover, order, width, height

ProductAttributeValue (catalog)
  product, attribute, value (JSON), numeric_value (dénormalisé)
  unique(product, attribute)

Favorite (catalog)
  user, product, created_at        unique(user, product)
```

### Messagerie

```
Conversation (messaging)
  participant_low, participant_high   (paire ordonnée)
  initial_product
  unique(participant_low, participant_high)

Message (messaging)
  conversation, sender, message_type (text|audio|product|system),
  body, shared_product, audio_file, audio_duration, created_at, read_at

ConversationBlock (messaging)   unique(conversation, blocked_by)
MessageReport (messaging)       message, reported_by, reason
```

### Notifications & analytics

```
Notification (notifications)
  user, type, title, message, url, data (JSON), read_at, created_at

ProductView (analytics)     product, user | visitor_id, created_at
SearchEvent (analytics)     query, normalized_query, filters (JSON), results_count
ContactEvent (analytics)    product, user, channel (phone|whatsapp)
DailyProductStats           product, date, views, unique_visitors  (préparé)
```

### Live

```
LiveSession (live)   host, title, description, status, thumbnail,
                     scheduled_for, started_at, ended_at, peak_viewers,
                     provider, provider_session_id, ingest_url, playback_url
LiveViewer (live)    live, user | visitor_id, joined_at, left_at
LiveMessage (live)   live, sender, message, product, created_at
LiveProduct (live)   live, product, position, is_featured   unique(live, product)
```

## Décisions de modélisation

**Attributs dynamiques (EAV ciblé).** `Product` ne contient aucun champ
propre à une catégorie. Ajouter « nombre de chambres » aux logements est une
opération d'administration, pas une migration. `ProductAttributeValue.value`
est un `JSONField` (un seul type de colonne pour texte, nombre, booléen,
date et multi-choix) et `numeric_value` est dénormalisé à l'enregistrement
pour que les filtres par plage restent indexables.

**Paire ordonnée pour les conversations.** `participant_low` /
`participant_high` (id le plus petit en premier) + contrainte d'unicité :
impossible de créer deux conversations entre les mêmes personnes selon
l'ordre de création.

**`is_active` distinct de `status`.** La modération contrôle `status` ; le
fournisseur contrôle `is_active`. Dépublier une annonce approuvée ne la
renvoie donc pas en file de modération.

**`master` sur les images.** L'original est conservé pour que recadrage et
rotation repartent toujours du fichier d'origine plutôt que de dégrader une
image déjà recompressée.

**Vues fiables.** `views_count` n'est incrémenté qu'après déduplication via
Redis (fenêtre de 12 h par utilisateur ou visiteur anonyme), avec un
`F()` atomique ; `ProductView` garde l'événement brut pour les séries
temporelles.

## Index

- `Product` : `(status, is_active, listing_type, city)` et
  `(category, status, is_active)` — les deux chemins de la recherche
  publique.
- `ProductAttributeValue` : `(attribute, numeric_value)` pour les filtres
  numériques par plage.
- `Message` : `(conversation, created_at)` pour la pagination du fil.
- `Notification` : `(user, read_at)` pour le compteur de non-lus.
- `LiveViewer` : `(live, left_at)` pour compter les présents.

## Migrations

```bash
python manage.py makemigrations          # après modification d'un modèle
python manage.py makemigrations --check  # vérifié en CI
python manage.py migrate
python manage.py migrate app 0003        # revenir à une version antérieure
```

Toutes les migrations ajoutées lors des dernières phases (favoris,
attributs, notifications, audio, live, `master`, `shares_count`) ont été
appliquées sur une base **existante contenant des données**, sans perte ni
recréation.

## Données de démonstration

```bash
python manage.py seed_demo   # idempotent
```

Crée catégories et attributs, 2 fournisseurs, 1 visiteur, 10 annonces avec
images, valeurs d'attributs, favoris, vues étalées sur 14 jours (pour que
les graphiques ne soient pas vides), contacts et notifications.

## Sauvegarde / restauration

```bash
pg_dump "$DATABASE_URL" -Fc -f nogoya-$(date +%F).dump
pg_restore -d "$DATABASE_URL" --clean --if-exists nogoya-2026-09-23.dump
```

Voir DEPLOYMENT.md pour la politique (fréquence, rétention, test de
restauration).
