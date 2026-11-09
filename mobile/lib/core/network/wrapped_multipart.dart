import 'dart:convert';
import 'dart:math';
import 'dart:typed_data';

// Encoder un corps multipart à la main, pour pouvoir l'étiqueter autrement.
//
// L'hébergement (LiteSpeed + ModSecurity) coupe la connexion — avant
// Django — dès qu'une requête annonce `multipart/form-data` et contient
// un `filename=`. Mesuré sur la production le 2026-11-09, au même
// point de terminaison :
//
//     avec un fichier, en multipart   -> connexion coupée (HTTP 000)
//     sans fichier, en multipart      -> 401, donc Django a répondu
//
// Le filtre ne regarde pas le contenu : il n'analyse le corps que
// lorsque l'en-tête annonce un formulaire. Le site contourne cela depuis
// des semaines (`frontend/src/lib/multipart.ts`) ; l'application mobile
// doit faire pareil, sinon aucune photo ne part depuis un téléphone.
//
// On produit donc le corps multipart nous-mêmes — ce que Dio ferait —
// pour en connaître la frontière, et on l'envoie en
// `application/octet-stream` avec la frontière dans un en-tête à part.
// Le serveur remet l'étiquette d'origine
// (`backend/apps/core/parsers.py`) : sur le réseau le format reste du
// multipart standard, seule l'étiquette change.

const uploadContentType = 'application/octet-stream';
const uploadBoundaryHeader = 'X-Upload-Boundary';

/// Une pièce fichier d'un envoi.
class UploadFile {
  const UploadFile({
    required this.field,
    required this.filename,
    required this.bytes,
    this.contentType = 'application/octet-stream',
  });

  final String field;
  final String filename;
  final Uint8List bytes;
  final String contentType;
}

/// Le corps encodé, et la frontière à placer dans l'en-tête.
class WrappedBody {
  const WrappedBody({required this.bytes, required this.boundary});

  final Uint8List bytes;
  final String boundary;

  Map<String, String> get headers => {
        'Content-Type': uploadContentType,
        uploadBoundaryHeader: boundary,
      };
}

/// Jeu de caractères volontairement étroit : le serveur le revalide avec
/// `[A-Za-z0-9_-]{8,70}`, et une frontière plus riche devrait être citée
/// dans l'en-tête reconstruit, donc pourrait y glisser un `;`.
String _randomBoundary() {
  final random = Random.secure();
  final hex = List.generate(16, (_) => random.nextInt(256).toRadixString(16).padLeft(2, '0')).join();
  return 'nogoya$hex';
}

/// Échappe une valeur d'en-tête de pièce, comme le fait un navigateur.
///
/// Un nom de fichier contenant un guillemet ou un retour à la ligne
/// fabriquerait sinon une pièce supplémentaire, choisie par celui qui a
/// nommé le fichier.
String _escape(String value) =>
    value.replaceAll('\r', '%0D').replaceAll('\n', '%0A').replaceAll('"', '%22');

/// Assemble les champs et les fichiers en un corps multipart.
WrappedBody encodeMultipart({
  Map<String, String> fields = const {},
  List<UploadFile> files = const [],
}) {
  final boundary = _randomBoundary();
  final out = BytesBuilder(copy: false);

  void writeAscii(String text) => out.add(utf8.encode(text));

  fields.forEach((name, value) {
    writeAscii('--$boundary\r\n');
    writeAscii('Content-Disposition: form-data; name="${_escape(name)}"\r\n\r\n');
    writeAscii(value);
    writeAscii('\r\n');
  });

  for (final file in files) {
    final filename = _escape(file.filename.isEmpty ? 'fichier' : file.filename);
    writeAscii('--$boundary\r\n');
    writeAscii(
      'Content-Disposition: form-data; name="${_escape(file.field)}"; '
      'filename="$filename"\r\n',
    );
    writeAscii('Content-Type: ${_escape(file.contentType)}\r\n\r\n');
    out.add(file.bytes);
    writeAscii('\r\n');
  }

  writeAscii('--$boundary--\r\n');
  return WrappedBody(bytes: out.takeBytes(), boundary: boundary);
}
