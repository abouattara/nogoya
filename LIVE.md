# Live — nogoya

État : **modèles et API en place, aucune infrastructure vidéo**. Un
fournisseur peut créer un live, y associer ses annonces, en épingler une et
recevoir des messages ; il n'y a pas encore de flux vidéo ni d'interface
dédiée. C'est délibéré : la vidéo est le poste de coût le plus lourd et
n'apporte rien tant que la marketplace n'a pas d'audience.

## Modèles (`apps/live`)

| Modèle | Rôle |
|---|---|
| `LiveSession` | la session : hôte, titre, description, statut, miniature, horaires, pic d'audience |
| `LiveViewer` | une présence (`joined_at` / `left_at`), utilisateur connecté ou visiteur anonyme |
| `LiveMessage` | le chat du live, avec un produit optionnellement référencé |
| `LiveProduct` | association live ↔ annonce, avec `position`, `is_featured` et la plage d'affichage |

Statuts : `draft` → `scheduled` → `live` → `ended` (ou `cancelled`).
Les brouillons ne sont visibles que de leur hôte.

Un seul produit peut être épinglé à la fois : `LiveProduct.feature()`
dépingle automatiquement le précédent et horodate la fin de son passage.

## API

| Endpoint | Description |
|---|---|
| `GET/POST /api/v1/lives/` | liste publique (hors brouillons) / création ; `?mine=true` pour les siens. La création répond avec la session complète (statut, hôte, produits), pas seulement les champs écrits |
| `PATCH /api/v1/lives/{id}/` | modification (hôte uniquement) |
| `POST /api/v1/lives/{id}/start/` | passe en direct, horodate `started_at` |
| `POST /api/v1/lives/{id}/end/` | termine et ferme les présences ouvertes |
| `POST /api/v1/lives/{id}/join/` \| `/leave/` | présence spectateur (anonyme accepté) |
| `GET/POST /api/v1/lives/{id}/products/` | annonces présentées (ajout réservé à l'hôte, et seulement ses propres annonces) |
| `POST /api/v1/lives/{id}/products/{product}/pin/` \| `/unpin/` | mise en avant |
| `GET/POST /api/v1/lives/{id}/messages/` | chat du live (lecture publique, écriture authentifiée) |

## Brancher un fournisseur vidéo plus tard

`LiveSession` porte quatre champs laissés vides, qui sont les points
d'ancrage prévus :

```
provider              "livekit" | "cloudflare" | "mux" ...
provider_session_id   identifiant de la room/stream chez le fournisseur
ingest_url            URL de publication (côté hôte)
playback_url          URL de lecture (côté spectateur)
```

L'intégration consiste à remplir ces champs dans `LiveSession.start()` en
appelant l'API du fournisseur, et à rendre `playback_url` dans un lecteur
côté frontend. **Aucun autre modèle n'a besoin de changer** : produits
épinglés, présences et chat sont déjà indépendants du transport vidéo.

Pistes par coût croissant : Cloudflare Stream Live (simple, facturé à la
minute), LiveKit Cloud (interactif, WebRTC), LiveKit auto-hébergé (le moins
cher à volume élevé, le plus lourd à exploiter).

## Ce qui manque

- Interface frontend (création, régie, page spectateur).
- Temps réel du chat de live (même choix que la messagerie : polling
  d'abord, WebSocket ensuite — l'infra Channels est déjà configurée).
- Notifications `LIVE_STARTED` aux abonnés d'un fournisseur.
