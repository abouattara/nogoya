# Stockage des fichiers — nogoya

Images produits, vocaux du chat et miniatures de live passent tous par le
même backend de stockage Django. L'application ne connaît jamais le
fournisseur : tout se règle par variables d'environnement.

## Les deux modes

| `USE_S3` | Backend | Usage |
|---|---|---|
| `False` (défaut) | `FileSystemStorage` (`backend/media/`) | Développement local sans Docker |
| `True` | `storages.backends.s3.S3Storage` | MinIO en local, Cloudflare R2 / AWS S3 en production |

Aucun code applicatif ne teste `USE_S3` : les `ImageField` / `FileField`
utilisent le storage par défaut, et `settings.base` choisit lequel.

## Variables d'environnement

```bash
USE_S3=True
S3_ENDPOINT=http://127.0.0.1:9000     # vide pour AWS S3 (endpoint par défaut)
S3_BUCKET=nogoya-media
S3_ACCESS_KEY=...
S3_SECRET_KEY=...
S3_REGION=auto                        # "auto" pour R2, ex "eu-west-3" pour AWS
S3_ADDRESSING_STYLE=path              # "path" pour MinIO, "virtual" pour AWS/R2
S3_PUBLIC_DOMAIN=media.nogoya.com     # domaine CDN devant le bucket (optionnel)
```

## MinIO en local

`docker compose up` démarre MinIO, crée le bucket et le rend lisible
publiquement (service `minio-setup`). Rien d'autre à faire.

- API S3 : http://localhost:9000
- Console : http://localhost:9001 (identifiants = `S3_ACCESS_KEY` / `S3_SECRET_KEY`)

Sans Docker :

```bash
docker run -p 9000:9000 -p 9001:9001 \
  -e MINIO_ROOT_USER=nogoyaminio -e MINIO_ROOT_PASSWORD=nogoyaminio123 \
  minio/minio server /data --console-address ":9001"
```

Puis créer le bucket depuis la console et passer `USE_S3=True` dans `.env`.

## Cloudflare R2 en production

```bash
USE_S3=True
S3_ENDPOINT=https://<account_id>.r2.cloudflarestorage.com
S3_BUCKET=nogoya-media
S3_ACCESS_KEY=<R2 access key>
S3_SECRET_KEY=<R2 secret key>
S3_REGION=auto
S3_ADDRESSING_STYLE=virtual
S3_PUBLIC_DOMAIN=media.nogoya.com     # domaine public R2 ou CDN devant
```

R2 est privilégié pour le MVP : pas de frais de sortie (egress), ce qui est
déterminant pour une marketplace riche en images.

Côté frontend, déclarer le même domaine pour `next/image` :

```bash
S3_PUBLIC_HOST=media.nogoya.com   # lu par next.config.ts (remotePatterns)
```

## Chaîne de traitement d'une image

Un seul pipeline (`apps/media/processing.py`) pour les photos d'annonces et
les images du chat — il y en avait deux qui faisaient à peu près la même
chose.

```
Upload
  → compression navigateur (canvas, ≤1280px, JPEG q0.82)
  → validation serveur (taille, MIME, décodage réel par Pillow)
  → rotation EXIF appliquée aux pixels, puis métadonnées supprimées
  → 3 rendus : master 1600px q80, display 900px q78, vignette 320px q70
  → storage (FileSystem, MinIO ou R2)
  → CDN
```

**Pourquoi compresser deux fois.** Le navigateur réduit avant l'envoi : sur
un téléphone en 3G, l'upload est la partie lente, et c'est de la donnée
payée des deux côtés. Le serveur recompresse quand même — un client est une
commodité, jamais une garantie.

**Ce qui est conservé, selon l'usage :**

| Usage | Stocké | Pourquoi |
|---|---|---|
| Photo d'annonce | `display` + `master` | Le master sert aux recadrages ultérieurs |
| Image de chat | `display` + vignette | Une photo de conversation se regarde, elle ne se ré-édite pas : un master par message doublerait la facture pour une taille que rien ne demande |

Le `master` d'une annonce n'est **plus** l'upload brut. Il valait jusqu'à
12 Mo de photo de téléphone, gardé indéfiniment au cas où. Un master à
1600px reste très au-delà de ce qu'un recadrage exige, pour une fraction du
coût ; la différence est invisible dans l'éditeur et très visible sur la
facture. Il est écrit une seule fois, au premier upload : recompresser après
une retouche ferait du fichier recadré le nouveau master, et le recadrage
suivant partirait d'une image déjà rognée.

**Pourquoi JPEG et pas WebP/AVIF.** Pillow écrit les trois. WebP gagnerait
~25 %, sur un format que tous les navigateurs, tous les robots et tous les
partages WhatsApp acceptent déjà. Le jour où la bande passante image devient
un vrai poste de coût, `IMAGE_FORMAT` dans `apps/media/processing.py` est le
seul endroit à changer.

**Métadonnées.** L'orientation EXIF est appliquée aux pixels (sinon une photo
droite dans la galerie arrive couchée dans le navigateur), puis tout l'EXIF
est supprimé au ré-encodage : une photo partagée ne doit pas transporter les
coordonnées GPS ni le modèle de téléphone de son auteur.

## Vidéos du chat

```
Sélection
  → durée et dimensions lues par le navigateur
  → image d'aperçu extraite (canvas, à 0,5 s pour éviter le noir du début)
  → refus immédiat si > 60 s ou > 100 Mo
  → validation serveur (taille, MIME, octets réels)
  → stockage tel quel + poster
```

**La vidéo n'est pas ré-encodée côté serveur, et c'est un choix.** Transcoder
exigerait ffmpeg dans l'image Docker (~100 Mo), un worker capable de le faire
tourner, et une file d'attente : beaucoup d'infrastructure pour un MVP dont
le chat n'a pas encore d'usagers. À la place, les limites (60 s, 100 Mo)
maintiennent les fichiers petits, et le téléphone a déjà encodé en H.264.

Le jour où transcoder se justifie, la couture est `apps/media/services.py`
(`build_video_attachment`) : y ajouter un appel à une tâche Celery qui
remplace le fichier et passe `status` de `processing` à `ready`. Les états
existent déjà côté API et interface.

**L'aperçu est extrait par le navigateur**, pas par le serveur : sinon il
faudrait décoder chaque vidéo uniquement pour afficher une vignette. C'est
ce poster qui permet de faire défiler une conversation sans télécharger une
seule vidéo.

## Fichiers audio (vocaux du chat)

Les vocaux ne sont **jamais** servis par une URL de stockage : le frontend
reçoit une URL d'API (`/api/v1/conversations/{id}/messages/{id}/audio/`)
qui vérifie l'appartenance à la conversation, puis **streame les octets**,
quel que soit le backend de stockage, avec `Cache-Control: private,
no-store`. Un utilisateur extérieur à la conversation reçoit un 404, même
avec l'URL exacte.

> Pourquoi pas une URL signée ? Parce que `AWS_QUERYSTRING_AUTH = False`
> (nécessaire aux images produits, servies publiquement) fait que
> `storage.url()` **ne signe rien** : le paramètre `expire` est ignoré et
> l'URL renvoyée reste valable indéfiniment. Le proxy par l'API est la
> seule garantie qui ne dépend pas d'un réglage de stockage. Un vocal pèse
> quelques centaines de kilo-octets, le coût est négligeable.

### Accès public du bucket : uniquement `products/`

L'anonyme ne doit pouvoir lire que le préfixe des images d'annonces.

```bash
# MinIO (fait automatiquement par docker compose)
mc anonymous set download local/nogoya-media/products

# Cloudflare R2 / S3 : n'exposer publiquement (domaine public ou CDN)
# que le préfixe products/ ; messages/audio/ doit rester privé.
```

Si le bucket entier est ouvert en lecture, un vocal reste atteignable par
son chemin (`messages/audio/<uuid>.webm`) malgré le contrôle d'accès de
l'API — c'est précisément le trou que ce découpage ferme.

## Limites d'upload

| Variable | Défaut | Portée |
|---|---|---|
| `MAX_IMAGE_UPLOAD_BYTES` | 12 Mo | images (annonces et chat) |
| `MAX_VIDEO_UPLOAD_BYTES` | 100 Mo | vidéos du chat |
| `MAX_AUDIO_UPLOAD_BYTES` | 10 Mo | vocaux |
| `MAX_VIDEO_DURATION_SECONDS` | 60 | vidéos du chat |
| `MAX_AUDIO_DURATION_SECONDS` | 300 | vocaux |
| `MAX_ATTACHMENTS_PER_MESSAGE` | 6 | pièces jointes par message |
| `ORPHAN_MEDIA_RETENTION_HOURS` | 24 | délai avant qu'un fichier sans référence soit balayable |

Toutes sont vérifiées côté serveur, en plus du contrôle des octets réels du
fichier (le `Content-Type` envoyé par le navigateur n'est jamais cru sur
parole). Le navigateur applique les mêmes limites avant l'envoi, par
courtoisie : annoncer « fichier trop volumineux » après deux minutes
d'upload est le pire moment possible.

## Arborescence du stockage

```
products/                        images d'annonces (préfixe public)
  <uuid>.jpg                     rendu affiché
  master-<uuid>.jpg              master optimisé (recadrages)
chat/<conversation>/<message>/   pièces jointes (privé)
  <uuid>.jpg|mp4|webm            fichier
  <uuid>-poster.jpg              vignette / image d'aperçu
messages/audio/                  vocaux antérieurs à la refonte (privé)
```

Le nom de fichier envoyé par l'utilisateur n'atteint jamais le stockage : il
pourrait contenir `../`, une double extension, ou simplement son nom. Seule
l'extension est conservée, après filtrage.

## Nettoyage des fichiers

Supprimer une ligne ne supprime pas un fichier : Django laisse les octets en
place. Sur un chat qui transporte des photos et des vidéos, cela revient à
payer tous les mois pour des médias que plus personne ne peut atteindre.

1. **Chemin normal** — un signal `post_delete`
   (`apps/media/signals.py`) supprime les fichiers quand une pièce jointe,
   un message ou une conversation disparaît. Il n'échoue jamais bruyamment :
   un incident de stockage ne doit pas transformer « le message est
   supprimé » en erreur 500.
2. **Filet de sécurité** — `python manage.py prune_media` compare le
   stockage à la base et signale les orphelins ; `--delete` les supprime.
   Les fichiers récents (moins de `ORPHAN_MEDIA_RETENTION_HOURS`) sont
   épargnés : un upload en cours appartient à une requête qui n'a pas encore
   validé sa transaction.

La liste des champs fichiers est obtenue **par introspection** des modèles,
pas écrite à la main : un champ ajouté plus tard et oublié dans cette
commande la ferait supprimer des fichiers vivants.

À planifier une fois par jour en production (`cron`, `systemd timer` ou
Celery beat) — voir DEPLOYMENT.md.

## Déduplication

`MessageAttachment.checksum` conserve le SHA-256 des octets stockés. Il n'est
pas utilisé pour dédupliquer aujourd'hui : sur un chat entre particuliers,
deux personnes envoient rarement le même fichier, et une déduplication
implique de compter les références avant chaque suppression. Le champ existe
pour que ce soit possible plus tard sans re-scanner tout le bucket, et il
permet d'identifier un fichier dans les journaux sans exposer sa clé.
