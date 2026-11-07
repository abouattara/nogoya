import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../network/api_client.dart';
import '../network/api_exception.dart';
import '../providers.dart';

/// L'enregistrement de cet appareil auprès de BINOGOYA.
///
/// Le serveur est prêt : `POST /api/v1/devices/` enregistre un jeton,
/// `DELETE /api/v1/devices/<jeton>/` le retire, et `notify()` pousse vers
/// tous les appareils d'une personne. Ce qui manque est le jeton
/// lui-même, que seul Firebase peut délivrer, et Firebase demande un
/// projet qui n'existe pas encore.
///
/// D'où cette couture. `register` prend un jeton et le fait connaître ;
/// `unregister` le retire à la déconnexion, sans quoi la personne
/// suivante sur ce téléphone recevrait les alertes de la précédente.
/// Le jour où `firebase_messaging` entre dans le projet, il n'y a qu'à
/// lui demander son jeton et appeler `register` : rien d'autre ne bouge.
///
/// Tant que personne n'appelle `register`, l'application fonctionne
/// entièrement. Les notifications restent lisibles dans l'application,
/// qui les relit du serveur ; il manque seulement l'alerte quand elle
/// est fermée.
class PushService {
  PushService(this._api);

  final ApiClient _api;

  /// Fait connaître cet appareil. Idempotent : le serveur réaffecte un
  /// jeton déjà vu plutôt que d'en créer un second.
  Future<bool> register(String token, {String platform = 'android'}) async {
    if (token.isEmpty) return false;
    try {
      await _api.post<Map<String, dynamic>>(
        '/devices/',
        data: {'token': token, 'platform': platform},
      );
      return true;
    } on ApiException {
      // Échouer ici ne doit rien casser : la personne garde ses
      // notifications dans l'application, elle n'a simplement pas
      // d'alerte quand celle-ci est fermée.
      return false;
    }
  }

  /// Retire cet appareil. À appeler **avant** d'effacer la session :
  /// l'appel demande encore le jeton d'accès de la personne qui part.
  Future<void> unregister(String token) async {
    if (token.isEmpty) return;
    try {
      await _api.delete<dynamic>('/devices/$token/');
    } on ApiException {
      // Le serveur nettoiera de lui-même au premier envoi refusé par
      // Firebase : un jeton mort se signale tout seul.
    }
  }
}

final pushServiceProvider = Provider<PushService>((ref) {
  return PushService(ref.watch(apiClientProvider));
});
