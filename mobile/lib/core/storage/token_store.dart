import 'dart:math';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Ou vivent le jeton de rafraichissement et l'identifiant de visiteur.
///
/// Deux rangements, parce que deux natures :
///
/// * Le **refresh token** ouvre le compte. Il va dans le coffre du
///   système (Keystore sur Android, Keychain sur iOS), jamais dans les
///   preferences, qu'une sauvegarde ou un téléphone root exposent.
/// * L'**access token** ne descend nulle part. Il vit en mémoire et meurt
///   avec l'application, comme sur le site. Il dure quelques minutes :
///   l'écrire sur le disque ajouterait une fuite possible pour epargner
///   un appel de rafraichissement.
/// * L'**identifiant de visiteur** n'identifie personne. Il sert a ne pas
///   compter dix fois la meme consultation et a appliquer les quotas ; les
///   preferences lui suffisent.
class TokenStore {
  TokenStore(this._secure, this._prefs);

  static const _refreshKey = 'binogoya.refresh_token';
  static const _visitorKey = 'binogoya.visitor_id';

  final FlutterSecureStorage _secure;
  final SharedPreferences _prefs;

  String? _accessToken;

  String? get accessToken => _accessToken;

  void setAccessToken(String? token) => _accessToken = token;

  Future<String?> readRefreshToken() async {
    try {
      return await _secure.read(key: _refreshKey);
    } on Exception {
      // Un coffre illisible (profil restaure, Keystore remis a zero) n'est
      // pas une panne : c'est une session perdue, et l'ecran de connexion
      // est la bonne réponse.
      return null;
    }
  }

  Future<void> saveRefreshToken(String token) async {
    await _secure.write(key: _refreshKey, value: token);
  }

  Future<void> clear() async {
    _accessToken = null;
    try {
      await _secure.delete(key: _refreshKey);
    } on Exception {
      // Rien a faire de plus : la session est déjà oubliee en mémoire.
    }
  }

  /// Trente-deux caractères hexadecimaux, le format que l'API valide.
  ///
  /// Genere une fois puis conserve : un nouvel identifiant a chaque
  /// lancement ferait passer la meme personne pour un visiteur inedit,
  /// et gonflerait les compteurs de vues de chaque annonce.
  String visitorId() {
    final existing = _prefs.getString(_visitorKey);
    if (existing != null && RegExp(r'^[0-9a-f]{32}$').hasMatch(existing)) {
      return existing;
    }
    final random = Random.secure();
    final generated = List.generate(
      32,
      (_) => random.nextInt(16).toRadixString(16),
    ).join();
    _prefs.setString(_visitorKey, generated);
    return generated;
  }
}
