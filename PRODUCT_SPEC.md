# Spécification produit — nogoya

Marketplace généraliste de location et de vente : véhicules, logements,
équipements, outils, électronique, vêtements, mobilier, matériel
événementiel/professionnel/agricole, objets divers.

## Rôles

- **Visiteur (non connecté)** : accueil, recherche, filtres (y compris par
  caractéristique), détail produit, catalogue fournisseur, suggestions
  personnalisées via le cookie visiteur. Ne peut ni contacter ni publier.
- **Utilisateur connecté** (`role=visitor`) : profil, favoris, historique de
  consultation et recommandations, messagerie (texte, produit joint,
  vocaux), notifications, contact fournisseur (téléphone révélé à la
  demande, WhatsApp si activé).
- **Fournisseur** (`role=supplier`) : tout ce que peut un utilisateur
  connecté + CRUD annonces avec attributs dynamiques, gestion et **retouche**
  des images (avant et après publication), publier/dépublier, tableau de
  bord avec statistiques et graphiques, sessions live (API).
- **Administrateur** : Django admin — modération des annonces, gestion des
  catégories **et de leurs attributs**, utilisateurs, fournisseurs,
  signalements, notifications.

## Parcours MVP livrés

```
Visiteur   : accueil → recherche → filtres (catégorie, ville, prix, type,
             caractéristiques) → produit → galerie → fournisseur →
             catalogue filtrable → localisation/Google Maps → partage
Utilisateur: inscription → connexion → tableau de bord (vus récemment,
             suggestions, nouveautés, recherches récentes) → favoris →
             contact (message interne, téléphone ou WhatsApp) →
             conversation (texte, annonce jointe, vocal) → notifications
Fournisseur: connexion → tableau de bord (tuiles + graphiques) → créer une
             annonce (attributs dynamiques, localisation, images retouchées)
             → (modération admin) → visible publiquement → publier/dépublier
             → MODIFIER l'annonce publiée → gérer et RETOUCHER les images →
             paramètres WhatsApp → sessions live (API)
Admin      : /admin/ → modération des annonces, catégories et attributs,
             signalements
```

Testé bout en bout dans le navigateur :
- 2026-09-21 : inscription fournisseur, connexion JWT, création de produit
  avec upload d'image réel, apparition en attente dans le dashboard,
  approbation via Django admin, visibilité publique + recherche,
  révélation du contact.
- 2026-09-22 : modification d'une annonce déjà publiée (titre changé,
  slug stable, repassage en modération vérifié en base), catalogue
  fournisseur avec filtres/tri/pagination, tableau de bord avec tuiles de
  statistiques réelles, gestion des images d'une annonce existante.
- 2026-09-23 : suite Playwright automatisée couvrant les parcours visiteur,
  utilisateur (favoris, chat, notifications, suggestions), fournisseur
  (création avec attributs, modification, retouche d'image publiée,
  graphiques, publier/dépublier), live (API) et mobile.

## Non couvert dans cette itération (voir TODO.md pour le détail)

Réservation et calendrier de disponibilité, interface frontend du live
(modèles et API prêts, pas d'infrastructure vidéo), suppression
d'arrière-plan et retouche assistée par IA, demande d'article
(« je ne trouve pas ce que je cherche »), récupération de mot de passe et
vérification du téléphone. Les commentaires produit ne sont pas prévus
(décision produit).

La messagerie interne est en temps réel par **polling**, pas par WebSocket
push (cf. ARCHITECTURE.md) ; le sélecteur de produit à joindre reste limité
côté visiteur (seulement le produit d'origine de la conversation).

## Modèle de données actuel

```
User (accounts)        — auth téléphone, role visitor|supplier
SupplierProfile         — 1-1 User, city/bio/is_verified/rating_avg
Category (catalog)      — arbre 2 niveaux (parent FK self)
Product (catalog)       — supplier FK, category FK, listing_type rent|sale,
                          rental_period, status pending|approved|rejected,
                          is_active (publié/dépublié par le fournisseur)
ProductImage (catalog)  — order, is_cover, width/height (post-compression)
ProductView (analytics) — log dédupliqué (12h) pour fiabiliser views_count
SearchEvent (analytics) — requêtes + filtres, anonymisé (visitor_id UUID)
ContactEvent (analytics)— révélation de contact (phone|whatsapp), pour la
                          stat "Contacts" du dashboard fournisseur
DailyProductStats       — agrégat quotidien (préparé, pas encore peuplé)
Conversation (messaging)— paire unique de participants, produit d'origine
Message (messaging)     — texte et/ou produit joint (shared_product)
ConversationBlock       — blocage d'une conversation par un participant
MessageReport           — signalement d'un message
```

`Product` porte aussi la localisation (`region`, `country`, `latitude`,
`longitude`, `place_id`, `location_precision`) et `shares_count`.
`SupplierProfile` porte `whatsapp_number` + `allow_whatsapp_contact`
(opt-in explicite, désactivé par défaut).

## Règles métier clés

- Toute modification du contenu d'un produit repasse son statut à
  `pending` (nouvelle modération obligatoire).
- Un produit approuvé peut être dépublié/republié par son fournisseur sans
  repasser par la modération (`is_active`).
- Le numéro de téléphone du fournisseur n'est jamais exposé aux visiteurs
  anonymes — uniquement aux utilisateurs authentifiés, à la demande
  (bouton "Afficher le contact").
- Une vue ne compte qu'une fois par visiteur/utilisateur toutes les 12h
  (déduplication Redis) ; le propriétaire qui consulte son propre produit
  n'incrémente jamais son propre compteur.
