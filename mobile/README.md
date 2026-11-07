# BINOGOYA mobile

L'application Android et iOS de la location BINOGOYA, en Flutter. Elle
parle à la même API Django que le site : il n'y a pas de second backend,
et aucune règle métier n'est réécrite ici.

## Lancer en développement

```bash
flutter pub get
flutter run --dart-define-from-file=env.dev.json
```

`env.dev.json` n'est pas dans le dépôt. Copiez `env.example.json` et
adaptez :

| Clé | À quoi elle sert |
|---|---|
| `API_BASE_URL` | la racine de l'API, sans barre oblique finale |
| `SITE_BASE_URL` | le site public, pour ouvrir les conditions d'utilisation |

**Depuis l'émulateur Android**, la machine hôte s'appelle `10.0.2.2`, pas
`localhost` : `localhost` désignerait le téléphone lui-même. Le serveur
Django doit écouter sur toutes les interfaces et accepter cet hôte :

```bash
python manage.py runserver 0.0.0.0:8000
```

`config/settings/dev.py` ajoute déjà `10.0.2.2` à `ALLOWED_HOSTS`. Sans
cela Django répond 400 et l'application affiche « les informations
envoyées ne sont pas valides », un message juste qui désigne le mauvais
coupable.

**Depuis un téléphone réel** branché sur le même Wi-Fi, mettez l'adresse
de la machine sur le réseau local (`http://192.168.1.12:8000`) et
ajoutez-la à `DJANGO_ALLOWED_HOSTS`.

## Construire un APK

```bash
flutter build apk --release --dart-define-from-file=env.prod.json
```

Le fichier sort dans `build/app/outputs/flutter-apk/`. Il se partage
directement : au Burkina Faso, l'installation par APK est plus courante
que le passage par le Play Store.

## Comment c'est rangé

```
lib/
  app/        la coquille à trois onglets et les routes
  core/
    config/   ce qui change d'un environnement à l'autre
    models/   les objets de l'API, lus à la main
    network/  le client HTTP, le rafraîchissement du jeton, les erreurs
    push/     l'enregistrement de l'appareil (voir plus bas)
    storage/  le coffre du jeton, l'identifiant de visiteur
    theme/    les couleurs du site, reprises telles quelles
  features/   un dossier par domaine : catalogue, demandes, messagerie,
              fournisseur, modération, compte, conditions
  shared/     ce que plusieurs écrans réutilisent
```

Les modèles sont écrits à la main plutôt que générés. Le projet n'a donc
ni `build_runner` ni fichiers `.g.dart` : une réponse d'API se lit dans
un seul fichier, et les lectures tolérantes (`intOf`, `dateOf`...) vivent
dans `core/models/paginated.dart`.

## Ce que l'application ne fait pas

* **Elle ne décide jamais d'un droit.** Masquer un bouton range l'écran,
  cela ne protège rien : chaque geste est revalidé par le serveur, qui
  refuse ce que le rôle n'autorise pas.
* **Elle n'affiche aucun numéro de téléphone de fournisseur.** Dans le
  schéma intermédié, les coordonnées ne circulent qu'après que l'équipe a
  vérifié la disponibilité. Le seul numéro visible est celui d'un
  demandeur sans compte, sur l'écran d'équipe, parce que le rappeler est
  la seule façon de lui répondre.
* **Elle n'écrit pas le jeton d'accès sur le disque.** Il vit en mémoire
  et meurt avec l'application, comme sur le site. Seul le jeton de
  rafraîchissement va dans le coffre du système.

## Notifications push : ce qu'il reste à faire

Le serveur est prêt et testé :

* `POST /api/v1/devices/` enregistre un appareil, `DELETE
  /api/v1/devices/<jeton>/` le retire ;
* `notify()` pousse vers tous les appareils d'une personne ;
* un jeton que Firebase rejette est supprimé tout seul ;
* sans configuration Firebase, rien ne part et **tout le reste
  fonctionne** : les notifications restent lisibles dans l'application,
  qui les relit du serveur.

Côté application, `core/push/push_service.dart` sait enregistrer et
retirer un jeton. Ce qui manque est le jeton lui-même, que seul Firebase
délivre. Trois étapes, dont la première ne peut pas être faite à votre
place :

1. **Créer le projet Firebase** sur console.firebase.google.com, y
   ajouter une application Android avec l'identifiant
   `com.binogoya.binogoya`, puis télécharger `google-services.json` et le
   déposer dans `android/app/`. Ce fichier ne se commite pas.
2. **Déposer le compte de service** (Paramètres du projet → Comptes de
   service → Générer une clé privée) **hors du dépôt**, sur le serveur,
   et renseigner dans son `.env` :

   ```
   FCM_CREDENTIALS_FILE=/chemin/hors/depot/fcm-service-account.json
   FCM_PROJECT_ID=binogoya-xxxxx
   ```

3. **Brancher le paquet** dans l'application :

   ```bash
   flutter pub add firebase_core firebase_messaging
   ```

   puis, au démarrage d'une session, demander le jeton à Firebase et le
   passer à `PushService.register`, et appeler `unregister` avant
   d'effacer la session à la déconnexion, sans quoi la personne suivante
   sur ce téléphone recevrait les alertes de la précédente.

Tant que l'étape 1 n'est pas faite, ne pas ajouter les paquets : le
greffon Gradle de Google fait échouer la compilation si
`google-services.json` manque.

## Vérifier

```bash
flutter analyze
flutter test
```
