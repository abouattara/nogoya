import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'network/api_client.dart';
import 'storage/token_store.dart';

/// Les preferences, injectees au demarrage.
///
/// Les lire est asynchrone, et un `FutureProvider` obligerait chaque
/// ecran a traverser un état de chargement pour une valeur disponible
/// avant le premier pixel. On les charge dans `main` et on remplace cette
/// valeur : le reste du code les lit comme une constante.
final sharedPreferencesProvider = Provider<SharedPreferences>(
  (ref) => throw UnimplementedError('Remplace dans main()'),
);

final secureStorageProvider = Provider<FlutterSecureStorage>(
  // Les options par defaut passent déjà par le Keystore sur Android et
  // le Keychain sur iOS : c'est tout ce qu'on demande a ce coffre.
  (ref) => const FlutterSecureStorage(),
);

final tokenStoreProvider = Provider<TokenStore>((ref) {
  return TokenStore(
    ref.watch(secureStorageProvider),
    ref.watch(sharedPreferencesProvider),
  );
});

/// Signale qu'une session est definitivement perdue.
///
/// Le client HTTP ne connait pas l'état de l'application et ne doit pas
/// le connaitre. Il pousse ici, et c'est le controleur de session qui
/// décide d'afficher l'ecran de connexion.
final sessionLostProvider = StateProvider<int>((ref) => 0);

final apiClientProvider = Provider<ApiClient>((ref) {
  return ApiClient(
    ref.watch(tokenStoreProvider),
    onSessionLost: () async {
      ref.read(sessionLostProvider.notifier).state++;
    },
  );
});
