# Alimenter le catalogue avant d'avoir des annonceurs

Une marketplace vide ne se remplit pas toute seule : personne ne publie sur
un site où personne ne cherche, et personne ne cherche sur un site vide.
Ce module casse ce cercle en référençant des annonces venues d'ailleurs, le
temps que les annonceurs de NOGOYA prennent le relais.

Il repose sur trois règles, et tout le reste en découle.

**On n'importe que ce qu'on a le droit d'importer.** Une source naît
désactivée et ne peut être activée sans qu'un humain ait écrit sur quelle
base l'import est autorisé. Les photos ne sont jamais reprises sauf
autorisation explicite et séparée.

**On n'invente rien.** Un prix illisible reste nul, une ville absente reste
vide, une catégorie douteuse reste à rattacher. L'annonce part en « données
insuffisantes » plutôt que d'entrer au catalogue avec une valeur plausible
et fausse.

**Aucun programme ne publie.** Tout import arrive en brouillon. Un humain
regarde, corrige, publie ou rejette.

---

## Ce qui est en place, et ce qui ne l'est pas

| | État |
| --- | --- |
| Modèles, migrations, déduplication, qualité, expiration | **fait** |
| Adaptateur fichier CSV (export partenaire) | **fait**, testé |
| Adaptateur flux RSS / Atom | **fait**, non éprouvé sur un vrai flux |
| Adaptateur API JSON générique | **fait**, aucune API connectée |
| Interface d'administration (imports + modération) | **fait** |
| Import récurrent (Celery + commande) | **fait** |
| Affichage public distinct pour les annonces externes | **fait** |
| Facebook Marketplace | **non fait, et volontairement** |

### Au sujet de Facebook

Aucune API publique de Meta ne donne accès aux annonces de Marketplace ni au
contenu des groupes. Il n'existe pas de permission à demander : la
fonctionnalité n'existe pas. Y accéder demanderait de simuler un
navigateur connecté avec le compte d'une personne, ce qui enfreint les
conditions d'utilisation, expose ce compte à la fermeture, et traite des
données personnelles sans base légitime.

Rien dans ce dépôt ne le fait, et rien n'est prévu pour le faire. Le chemin
praticable pour un bien vu sur Facebook est la **soumission manuelle** :
l'administrateur crée l'annonce depuis l'interface, avec l'accord du
propriétaire, ou la référence avec un lien vers la publication d'origine.

Si Meta ouvrait un jour un accès, il se brancherait par l'adaptateur
`api` : une source à créer, une configuration à remplir, aucun déploiement.

---

## Fichiers

### Créés

| Fichier | Rôle |
| --- | --- |
| `backend/apps/sourcing/models.py` | `ListingSource`, `ListingImport` |
| `backend/apps/sourcing/net.py` | Téléchargement protégé contre les SSRF |
| `backend/apps/sourcing/normalization.py` | Prix, périodes, catégories, URL |
| `backend/apps/sourcing/fingerprints.py` | Empreinte et doublons probables |
| `backend/apps/sourcing/quality.py` | Ce qu'une annonce doit avoir |
| `backend/apps/sourcing/services.py` | Le pipeline et son rapport |
| `backend/apps/sourcing/adapters/base.py` | Contrat commun, registre |
| `backend/apps/sourcing/adapters/csv_file.py` | Export CSV partenaire |
| `backend/apps/sourcing/adapters/feed.py` | RSS / Atom (`xml.etree`) |
| `backend/apps/sourcing/adapters/json_api.py` | API JSON générique |
| `backend/apps/sourcing/admin.py` | Écrans d'import et de validation |
| `backend/apps/sourcing/tasks.py` | Import récurrent |
| `backend/apps/sourcing/management/commands/import_listings.py` | Lancement manuel |
| `backend/apps/sourcing/management/commands/prune_import_payloads.py` | Purge des données brutes |
| `backend/apps/sourcing/tests.py` | 33 tests |
| `frontend/src/components/product/ExternalListingCard.tsx` | Panneau « annonce référencée » |

### Modifiés

| Fichier | Changement |
| --- | --- |
| `backend/apps/catalog/models.py` | `provenance`, `source`, `source_url`, `last_checked_at`, quatre statuts |
| `backend/apps/catalog/serializers.py` | `provenance`, `source`, `supplier` nul pour l'externe |
| `backend/apps/catalog/filters.py` | `provenance`, `source`, `area`, `rental_period` |
| `backend/apps/catalog/api.py` | `/contact/` refusé pour une annonce externe |
| `backend/apps/catalog/admin.py` | Modération : publier, rejeter, indisponible, archiver |
| `backend/config/settings/base.py` | `apps.sourcing`, `SOURCING_IMPORT_DIR` |
| `frontend/src/lib/types.ts` | `Provenance`, statuts, `source` |
| `frontend/src/components/product/ProductCard.tsx` | Mention de la source |
| `frontend/src/components/search/FiltersSidebar.tsx` | Filtres origine et quartier |
| `frontend/src/app/produits/[slug]/page.tsx` | Deux parcours selon la provenance |

---

## Statuts

Le vocabulaire demandé est en place. Deux codes n'ont **pas** été renommés :

| Demandé | Code en base | Pourquoi |
| --- | --- | --- |
| `draft` | `draft` | |
| `pending_review` | `pending` | Déjà écrit en production, comparé par le frontend et les tests E2E |
| `published` | `approved` | Idem |
| `rejected` | `rejected` | |
| `expired` | `expired` | |
| `unavailable` | `unavailable` | |
| `archived` | `archived` | |

Renommer deux valeurs présentes dans une base vivante, dans le code client
et dans les tests de bout en bout, aurait apporté un libellé contre un
risque réel. Les libellés affichés, eux, disent « En attente de validation »
et « Publiée ».

## Provenance

| Valeur | Signification | Parcours visiteur |
| --- | --- | --- |
| `nogoya_owner` | Bien géré par un membre | Contact et messagerie NOGOYA |
| `authorized_partner` | Bien fourni par un partenaire | Renvoi vers le partenaire |
| `external_reference` | Annonce référencée | Renvoi vers l'annonce d'origine |

`Product.supplier` reste obligatoire : des dizaines d'endroits lisent
`product.supplier.user`. Pour une annonce importée, il désigne un **compte
de service** — inactif, sans mot de passe utilisable, nommé « NOGOYA —
annonces référencées ». Ce n'est pas un faux propriétaire : les
sérialiseurs renvoient `supplier: null` pour toute annonce externe, et
`supplier_name` donne le nom de la source. `/contact/` répond **409** avec
l'URL d'origine.

---

## Variables d'environnement

| Variable | Défaut | Rôle |
| --- | --- | --- |
| `SOURCING_IMPORT_DIR` | `backend/imports` | Dossier où les partenaires déposent leurs CSV |
| *(par source)* | — | `ListingSource.credential_env_var` nomme la variable portant la clé d'API |

Aucune clé n'est stockée en base ni dans le dépôt : la source enregistre le
**nom** de la variable, jamais sa valeur. Ajoutez-la au `.env` du serveur.

---

## Installation

Aucune dépendance nouvelle — `urllib`, `csv` et `xml.etree` suffisent, ce
qui maintient la liste des paquets inchangée.

```bash
cd backend
python manage.py migrate
mkdir -p imports          # si vous attendez des CSV partenaires
```

---

## Configurer une source

Administration Django → **Sources d'annonces** → Ajouter.

### Fichier CSV d'un partenaire

Déposez l'export dans `backend/imports/`, puis :

- **Type** : Fichier CSV fourni par un partenaire
- **Point d'accès** : `parc-agence-x.csv` (nom seul, le chemin est contraint
  au dossier d'import)
- **Autorisation** : « Export fourni par l'agence X, courriel du 20/10/2026 »
- **Active** : oui
- **Configuration** :

```json
{
  "adapter": "file",
  "delimiter": ";",
  "default_listing_type": "rent",
  "fields": {
    "title": "Libelle",
    "description": "Descriptif",
    "price_text": "Loyer",
    "city": "Ville",
    "area": "Quartier",
    "category": "Categorie",
    "original_url": "Lien",
    "external_id": "Reference"
  }
}
```

Les colonnes non listées gardent leur nom par défaut. Les photos se
déclarent dans une colonne unique, séparées par `|`, et ne sont retenues que
si **réutilisation des photos autorisée** est cochée.

### Flux RSS

- **Type** : Flux RSS / Atom, **Point d'accès** : l'URL du flux
- **Configuration** : `{"adapter": "feed", "city": "Ouagadougou", "category_hint": "Appartements"}`

Un flux ne porte ni prix ni ville de façon structurée : ils sont cherchés
dans le texte et, à défaut, l'annonce part en examen manuel. C'est voulu.

### API JSON

- **Configuration** : `{"adapter": "api", "items_path": "data.results", "fields": {...}}`
- **Variable d'environnement portant la clé** : `PARTENAIRE_X_API_KEY`

---

## Lancer un import

Commencez toujours par une simulation :

```bash
python manage.py import_listings --source agence-x --dry-run
```

Puis, pour de bon, en plafonnant la première fois :

```bash
python manage.py import_listings --source agence-x --limit 10
```

Toutes les sources actives dont l'intervalle est écoulé :

```bash
python manage.py import_listings --all
```

Depuis l'administration : sélectionner la source → action « Lancer l'import
maintenant » ou « Simuler l'import ».

### Automatisation

Avec un worker Celery, la tâche `apps.sourcing.tasks.run_scheduled_imports`
parcourt les sources actives et saute celles relancées trop tôt.

Sur l'hébergement mutualisé il n'y a pas de worker : programmez une tâche
cron cPanel.

```bash
cd ~/nogoya/backend && ~/virtualenv/nogoya/backend/3.11/bin/python manage.py import_listings --all
```

L'intervalle est porté par la source (`min_interval_minutes`, 6 h par
défaut), pas par la planification : une tâche cron horaire n'interrogera pas
pour autant une source qui n'accepte qu'un passage par jour.

---

## Validation et publication

Administration → **Annonces importées**. Filtres par statut, source,
catégorie, ville.

| Statut | Signification |
| --- | --- |
| À examiner | Rencontrée, pas encore traitée |
| Importée en brouillon | Un produit existe, en attente de validation |
| Doublon probable | Rapprochée d'une annonce existante — rien n'a été créé |
| Données insuffisantes | Motif dans « message d'erreur » |
| Erreur de traitement | Incident technique |
| Disparue de la source | Plus présente ; l'annonce est passée en « Expirée » |

Actions : **Publier**, **Rejeter**, **Marquer indisponible**. Le lien « Voir
l'annonce » ouvre la source dans un nouvel onglet — vérifiez-le avant de
publier.

Les annonces des membres se modèrent au même endroit, dans
**Catalogue → Produits**, avec les mêmes actions plus **Archiver**, qui sert
aux retraits sur demande d'un propriétaire ou d'une source.

---

## Déduplication

Deux mécanismes distincts :

**L'empreinte** répond à « déjà vue chez cette source ? ». Elle s'appuie sur
l'identifiant externe, sinon sur l'URL normalisée (sans `www.`, sans
paramètres de suivi), sinon sur titre + ville + catégorie + prix. Revoir la
même annonce met la ligne à jour ; elle n'en crée pas une seconde.

**Le rapprochement** répond à « ce bien existe-t-il déjà, venu d'ailleurs ? ».
Ville, catégorie et prix doivent concorder, **et** les titres se recouvrir à
60 %. Le titre seul ne décide jamais : « Appartement 2 chambres à Ouaga
2000 » désigne cinquante biens. En cas de soupçon, rien n'est créé ni
fusionné : la ligne passe en « Doublon probable » avec la référence de
l'annonce jumelle.

## Expiration

Une annonce que la source ne présente plus passe en « Expirée » et quitte le
catalogue public.

La distinction qui compte : une source **en panne** lève une erreur (HTTP en
échec, flux vide, fichier absent) et l'expiration est alors suspendue — une
panne ne doit pas vider le catalogue. Une source qui répond correctement
sans aucune annonce, elle, signifie bien que tout a disparu.

Si l'annonce réapparaît, elle redevient un brouillon à revoir. Une annonce
**rejetée** par un modérateur, en revanche, n'est jamais ressuscitée par une
exécution suivante.

---

## Sécurité

- **SSRF** : toute URL est résolue avant appel et chaque adresse obtenue doit
  être publique — la boucle locale, les réseaux privés et `169.254.169.254`
  (les identifiants de la machine chez la plupart des hébergeurs) sont
  refusés. Les redirections sont suivies à la main, chacune revalidée : les
  laisser à `urllib` ne contrôlerait que le premier saut. Seuls `http` et
  `https` passent, la réponse est bornée à 8 Mo.
- **Traversée de chemin** : `endpoint` vient de l'admin ; le fichier est
  résolu puis vérifié comme appartenant au dossier d'import, ce qui ferme
  `../../.env`.
- **Échappement** : les liens de source sont rendus par `format_html` côté
  admin et par React côté public, donc échappés. Les liens sortants portent
  `noopener noreferrer nofollow`.
- **Secrets** : jamais en base, jamais dans Git — seul le nom de la variable
  d'environnement est enregistré.
- **Données personnelles** : les coordonnées ne sont conservées que si la
  source déclare des coordonnées professionnelles publiables. Les données
  brutes sont purgées par `prune_import_payloads` (30 jours par défaut).
- **Retrait** : action « Archiver » dans l'administration des produits ;
  désactiver la source empêche toute réapparition.

---

## Tests

```bash
cd backend && python manage.py test apps.sourcing      # 33 tests
cd frontend && npx vitest run src/components/product/ExternalListingCard.test.tsx
```

Aucun ne touche le réseau : les adaptateurs sont remplacés par des doubles,
et la source fichier lit un CSV écrit dans un dossier temporaire.

---

## Limites connues

- **Aucune source réelle n'est connectée.** Le pipeline est complet et
  testé, mais il n'y a aujourd'hui ni flux ni API autorisés. La première
  source utilisable sera un export CSV d'agence, qui ne demande qu'un
  accord et un fichier.
- **L'adaptateur RSS n'a jamais vu de vrai flux.** Il est testé sur du XML
  construit pour les tests. Prévoyez un `--dry-run` sur le premier flux réel.
- **Pas d'import de photos.** Même autorisées, les photos sont seulement
  mémorisées comme URL dans `normalized["image_urls"]` ; leur téléchargement
  n'est pas implémenté. Une annonce référencée s'affiche donc sans photo,
  et renvoie vers la source — ce qui est le comportement le plus prudent.
- **Pas d'Excel.** Les partenaires exportent en CSV ; ajouter `openpyxl`
  pour une poignée de fichiers n'a pas paru justifié.
- **Rattachement de catégorie limité.** Au-delà de la correspondance par
  nom, une poignée de mots-clés. Un cas douteux part en examen manuel
  plutôt que d'être rangé au hasard.
- **Pas de géocodage.** Latitude et longitude restent nulles pour une
  annonce importée.
