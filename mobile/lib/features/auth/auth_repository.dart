import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/models/user.dart';
import '../../core/network/api_client.dart';
import '../../core/providers.dart';
import '../../core/storage/token_store.dart';

/// La version des conditions d'utilisation que l'application affiche.
///
/// Doit rester egale a `backend/apps/legal/terms.py` et a
/// `frontend/src/content/conditions.ts`. Le serveur refuse une
/// inscription qui porte une autre version, avec un message demandant de
/// mettre a jour : c'est voulu, un accord doit porter sur le texte lu.
const kTermsVersion = '2026-11-05';

class AuthRepository {
  AuthRepository(this._api, this._tokens);

  final ApiClient _api;
  final TokenStore _tokens;

  /// Ouvre une session et garde les deux jetons.
  Future<CurrentUser> login({required String phone, required String password}) async {
    final data = await _api.post<Map<String, dynamic>>(
      '/auth/login/',
      data: {'phone': phone, 'password': password},
    );
    await _storeTokens(data);
    return me();
  }

  /// Cree un compte. L'acceptation des conditions part avec.
  ///
  /// Le serveur l'exige et inscrit une ligne datee portant la version :
  /// ne pas l'envoyer donne un 400, pas un compte sans trace.
  Future<void> register({
    required String phone,
    required String firstName,
    required String lastName,
    required String password,
    required UserRole role,
    required bool acceptTerms,
  }) async {
    await _api.post<Map<String, dynamic>>(
      '/auth/register/',
      data: {
        'phone': phone,
        'first_name': firstName,
        'last_name': lastName,
        'role': role.wire,
        'password': password,
        'password2': password,
        'accept_terms': acceptTerms,
        'terms_version': kTermsVersion,
      },
    );
  }

  Future<CurrentUser> me() async {
    final data = await _api.get<Map<String, dynamic>>('/auth/me/');
    return CurrentUser.fromJson(data);
  }

  /// Reprend la session d'un lancement precedent, s'il en reste une.
  ///
  /// Le jeton d'acces ne survit pas a la fermeture : on repart du refresh
  /// garde dans le coffre. Null veut dire « personne n'est connecte », ce
  /// qui est un état normal, pas une panne.
  Future<CurrentUser?> restore() async {
    final refresh = await _tokens.readRefreshToken();
    if (refresh == null) return null;
    try {
      final data = await _api.post<Map<String, dynamic>>(
        '/auth/refresh/',
        data: {'refresh': refresh},
      );
      await _storeTokens(data);
      return me();
    } on Exception {
      await _tokens.clear();
      return null;
    }
  }

  Future<void> logout() async {
    final refresh = await _tokens.readRefreshToken();
    // On efface d'abord : si le réseau est coupe, la session doit quand
    // meme se fermer sur ce téléphone. Le serveur finira d'expirer seul.
    await _tokens.clear();
    if (refresh == null) return;
    try {
      await _api.post<Map<String, dynamic>>('/auth/logout/', data: {'refresh': refresh});
    } on Exception {
      // Deconnecte localement : c'est ce qui compte pour la personne.
    }
  }

  Future<void> _storeTokens(Map<String, dynamic> data) async {
    final access = data['access'] as String?;
    final refresh = data['refresh'] as String?;
    if (access != null) _tokens.setAccessToken(access);
    if (refresh != null) await _tokens.saveRefreshToken(refresh);
  }
}

final authRepositoryProvider = Provider<AuthRepository>((ref) {
  return AuthRepository(ref.watch(apiClientProvider), ref.watch(tokenStoreProvider));
});
