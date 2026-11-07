import 'package:flutter/material.dart';

/// Les couleurs de BINOGOYA, reprises telles quelles du site.
///
/// Les valeurs viennent de `frontend/src/app/globals.css`. Les recopier
/// plutot que de les reinventer evite qu'une annonce vue sur le téléphone
/// et la meme annonce vue sur le site paraissent appartenir a deux
/// marques. Les rapports de contraste notes en commentaire ont ete
/// mesures lors de la refonte du design sur le logo ; ils valent ici
/// aussi, et c'est ce qui interdit le texte blanc sur `accent500`.
abstract final class AppColors {
  // Indigo du ruban du logo.
  static const brand50 = Color(0xFFF3F2FA);
  static const brand100 = Color(0xFFE5E3F4);
  static const brand200 = Color(0xFFC9C5E8);
  static const brand300 = Color(0xFFA49ED6);
  static const brand400 = Color(0xFF7B73BE);
  static const brand500 = Color(0xFF574EA1);

  /// Primaire. Blanc dessus : 12,3:1.
  static const brand600 = Color(0xFF312A73);

  /// Survol et presse : 14,0:1.
  static const brand700 = Color(0xFF29235F);
  static const brand800 = Color(0xFF1F1A4A);
  static const brand900 = Color(0xFF161236);

  // Corail du logo.
  static const accent50 = Color(0xFFFEF1F2);
  static const accent100 = Color(0xFFFDE2E5);
  static const accent200 = Color(0xFFFAC4CB);
  static const accent300 = Color(0xFFF59AA6);
  static const accent400 = Color(0xFFEF7080);

  /// La couleur du logo. Jamais de texte blanc dessus.
  static const accent500 = Color(0xFFE75267);

  /// Le seul corail qui porte du blanc (4,7:1).
  static const accent600 = Color(0xFFD23A52);
  static const accent700 = Color(0xFFAE2C41);

  static const background = Color(0xFFFFFFFF);
  static const surface = Color(0xFFFFFFFF);
  static const surfaceMuted = brand50;
  static const surfaceHover = brand100;

  /// Presque noir, sous-teinte indigo : 16,9:1.
  static const foreground = Color(0xFF1C1A33);

  /// Texte secondaire : 7,5:1 sur blanc.
  static const foregroundMuted = Color(0xFF565073);

  static const border = Color(0xFFE3E0F1);
  static const borderStrong = brand300;

  static const successBg = Color(0xFFDCFCE7);
  static const successFg = Color(0xFF166534);
  static const warningBg = Color(0xFFFEF3C7);
  static const warningFg = Color(0xFF92400E);
  static const dangerBg = Color(0xFFFEE2E2);
  static const dangerFg = Color(0xFFB91C1C);
  static const danger600 = Color(0xFFDC2626);
}
