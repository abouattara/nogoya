import 'dart:typed_data';

import 'package:flutter_image_compress/flutter_image_compress.dart';

/// Ce qu'un envoi peut peser pour arriver à coup sûr.
///
/// L'hébergeur coupe toute requête dont l'envoi dure plus d'une trentaine
/// de secondes. Mesuré en production le 2026-11-17 avec la même photo
/// d'1 Mo : à ~50 Ko/s elle passe en 19 s, à ~20 Ko/s la connexion est
/// fermée par le serveur au bout de 37 s. Un réseau mobile ordinaire
/// envoie entre 10 et 50 Ko/s : c'est donc le poids, et non le format,
/// qui décidait si une photo partait.
///
/// Les budgets visent une quinzaine de secondes à 20 Ko/s, la moitié de
/// la limite, pour laisser de la marge à un réseau plus mauvais encore.
abstract final class UploadBudget {
  /// Une photo de discussion : vue sur un écran de téléphone.
  static const chatPhotoBytes = 280 * 1024;

  /// Une photo d'annonce : le serveur en garde un original de 1600 px,
  /// elle mérite un peu plus de place.
  static const listingPhotoBytes = 400 * 1024;

  /// La plus longue arête, imposée au moment du choix. C'est le
  /// sélecteur de photos qui la tient : lui la traite comme un maximum.
  static const chatPhotoEdge = 1280.0;
  static const listingPhotoEdge = 1600.0;

  /// La qualité de départ, avant tout ajustement.
  static const startQuality = 75;
}

/// Ramène une photo sous son budget en baissant seulement la qualité.
///
/// Les dimensions sont déjà plafonnées par le sélecteur. On ne les
/// touche pas ici : `flutter_image_compress` traite `minWidth` et
/// `minHeight` comme des **minimums** (son échelle est le plus petit des
/// deux rapports), si bien qu'y passer 1280 produirait une image plus
/// grande que prévu sur son grand côté. Des bornes démesurées gardent
/// donc l'échelle à 1, et seule la qualité change.
///
/// Rend les octets d'origine s'ils tiennent déjà, et le meilleur résultat
/// obtenu sinon : mieux vaut tenter un envoi un peu lourd que de ne rien
/// envoyer du tout.
Future<Uint8List> fitPhotoToBudget(Uint8List bytes, int budget) async {
  if (bytes.length <= budget) return bytes;
  var best = bytes;
  for (final quality in const [62, 50, 40]) {
    try {
      final out = await FlutterImageCompress.compressWithList(
        bytes,
        minWidth: 100000,
        minHeight: 100000,
        quality: quality,
        format: CompressFormat.jpeg,
      );
      if (out.isEmpty) continue;
      if (out.length < best.length) best = out;
      if (out.length <= budget) return out;
    } on Exception {
      // Un format que le compresseur ne lit pas : on garde l'original.
      return best;
    }
  }
  return best;
}
