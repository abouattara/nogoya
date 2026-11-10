import 'package:flutter/material.dart';

/// Les couleurs de BINOGOYA, reprises telles quelles du site.
///
/// Les valeurs viennent de `frontend/src/app/globals.css`, elles-mêmes
/// échantillonnées dans le logo : le bleu de « BINOG », l'orange de
/// « OYA ». Les recopier plutôt que de les réinventer évite qu'une annonce
/// vue sur le téléphone et la même annonce vue sur le site paraissent
/// appartenir à deux marques.
///
/// Les rapports de contraste notés en commentaire ont été mesurés. Deux
/// couleurs du logo ne portent pas de texte blanc : le bleu `brand500`
/// (4,2:1, sous le seuil de 4,5) et l'orange `accent500` (2,0:1). Un
/// bouton prend `brand600` ; sur l'orange, le texte est foncé.
abstract final class AppColors {
  // Bleu du logo.
  static const brand50 = Color(0xFFEFF7FC);
  static const brand100 = Color(0xFFDCEDF8);
  static const brand200 = Color(0xFFB5D9F0);
  static const brand300 = Color(0xFF7FBDE4);
  static const brand400 = Color(0xFF3C9BD6);

  /// La couleur du logo. Blanc dessus : 4,2:1, trop peu pour du texte.
  static const brand500 = Color(0xFF0080CC);

  /// Primaire. Blanc dessus : 5,7:1.
  static const brand600 = Color(0xFF006BAD);

  /// Survol et pressé : 7,3:1.
  static const brand700 = Color(0xFF005A94);
  static const brand800 = Color(0xFF004876);
  static const brand900 = Color(0xFF003556);

  // Orange du logo.
  static const accent50 = Color(0xFFFFF8ED);
  static const accent100 = Color(0xFFFEECD0);
  static const accent200 = Color(0xFFFDD9A0);
  static const accent300 = Color(0xFFFBC16B);
  static const accent400 = Color(0xFFF9B24F);

  /// La couleur du logo. Texte foncé dessus (7,4:1), jamais blanc (2,0:1).
  static const accent500 = Color(0xFFF7A53B);

  /// Le seul orange qui porte du blanc (5,0:1).
  static const accent600 = Color(0xFFA85D08);
  static const accent700 = Color(0xFF8F4E08);

  static const background = Color(0xFFFFFFFF);
  static const surface = Color(0xFFFFFFFF);
  static const surfaceMuted = brand50;
  static const surfaceHover = brand100;

  /// Presque noir, sous-teinte bleue : 14,9:1.
  static const foreground = Color(0xFF13293D);

  /// Texte secondaire : 6,9:1 sur blanc.
  static const foregroundMuted = Color(0xFF475C71);

  static const border = Color(0xFFDBE6EF);
  static const borderStrong = brand300;

  static const successBg = Color(0xFFDCFCE7);
  static const successFg = Color(0xFF166534);
  static const warningBg = Color(0xFFFEF3C7);
  static const warningFg = Color(0xFF92400E);
  static const dangerBg = Color(0xFFFEE2E2);
  static const dangerFg = Color(0xFFB91C1C);
  static const danger600 = Color(0xFFDC2626);
}
