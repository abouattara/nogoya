/// Ce qui change d'un environnement a l'autre.
///
/// Rien n'est ecrit en dur dans le code et rien n'est commite : l'adresse
/// de l'API arrive par `--dart-define`, ou par `--dart-define-from-file`
/// avec le fichier decrit dans `mobile/env.example.json`. Une adresse de
/// production gravee dans les sources suivrait chaque compilation de
/// developpement, et l'inverse est pire encore.
///
///     flutter run --dart-define-from-file=env.dev.json
///     flutter build apk --dart-define-from-file=env.prod.json
abstract final class AppConfig {
  /// La racine de l'API, sans barre oblique finale.
  ///
  /// Par defaut `10.0.2.2:8000`, qui est la facon dont l'emulateur Android
  /// joint le `localhost` de la machine hote. Depuis un téléphone reel,
  /// `localhost` designerait le téléphone lui-meme : il faut alors passer
  /// l'adresse de la machine sur le réseau local.
  static const apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://10.0.2.2:8000',
  );

  /// L'adresse du site public, pour ouvrir ce que l'application ne
  /// reproduit pas : les conditions d'utilisation, par exemple, qui
  /// doivent etre lues dans la version que le serveur fait foi plutot que
  /// dans une copie figee au moment de la compilation.
  static const siteBaseUrl = String.fromEnvironment(
    'SITE_BASE_URL',
    defaultValue: 'https://binogoya.com',
  );

  /// Vrai en production : coupe les journaux réseau, qui recopient des
  /// corps de requete entiers et donc, le jour de la connexion, un mot de
  /// passe en clair dans le journal du système.
  static const isRelease = bool.fromEnvironment('dart.vm.product');

  static String get apiRoot => '$apiBaseUrl/api/v1';
}
