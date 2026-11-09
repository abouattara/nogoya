import 'dart:convert';
import 'dart:typed_data';

import 'package:binogoya/core/network/wrapped_multipart.dart';
import 'package:flutter_test/flutter_test.dart';

Uint8List octets(String texte) => Uint8List.fromList(utf8.encode(texte));

void main() {
  group('encodeMultipart', () {
    test("annonce l'octet-stream et sort la frontière à part", () {
      // C'est tout l'objet de cet encodage : ModSecurity coupe la
      // connexion dès qu'une requête annonce un formulaire et contient un
      // `filename=`. L'étiquette change, le corps reste du multipart.
      final body = encodeMultipart(files: [
        UploadFile(field: 'images', filename: 'photo.jpg', bytes: octets('xx')),
      ]);

      expect(body.headers['Content-Type'], 'application/octet-stream');
      expect(body.headers['X-Upload-Boundary'], body.boundary);
    });

    test('produit une frontière que le serveur accepte', () {
      // Le serveur revalide avec `[A-Za-z0-9_-]{8,70}` : une frontière
      // hors de ce jeu ferait rejeter l'envoi, et le message d'erreur ne
      // parlerait pas de frontière.
      final motif = RegExp(r'^[A-Za-z0-9_-]{8,70}$');
      for (var i = 0; i < 20; i++) {
        expect(motif.hasMatch(encodeMultipart().boundary), isTrue);
      }
    });

    test('deux envois ne partagent pas la même frontière', () {
      expect(encodeMultipart().boundary, isNot(encodeMultipart().boundary));
    });

    test('écrit les champs et les fichiers au format multipart', () {
      final body = encodeMultipart(
        fields: {'body': 'bonjour'},
        files: [
          UploadFile(
            field: 'images',
            filename: 'photo.jpg',
            bytes: octets('OCTETS'),
            contentType: 'image/jpeg',
          ),
        ],
      );
      final texte = utf8.decode(body.bytes);
      final b = body.boundary;

      expect(
        texte,
        contains('--$b\r\nContent-Disposition: form-data; name="body"\r\n\r\nbonjour\r\n'),
      );
      expect(
        texte,
        contains('Content-Disposition: form-data; name="images"; filename="photo.jpg"\r\n'
            'Content-Type: image/jpeg\r\n\r\nOCTETS\r\n'),
      );
      expect(texte, endsWith('--$b--\r\n'));
    });

    test("un nom de fichier ne peut pas fabriquer une pièce de plus", () {
      // Sans échappement, un guillemet et un retour à la ligne dans le nom
      // laisseraient celui qui nomme le fichier ajouter ses propres
      // en-têtes de pièce, donc ses propres champs.
      final body = encodeMultipart(files: [
        UploadFile(
          field: 'images',
          filename: 'x"\r\nContent-Disposition: form-data; name="role"\r\n\r\nadmin',
          bytes: octets('z'),
        ),
      ]);
      final texte = utf8.decode(body.bytes);

      expect(texte, isNot(contains('name="role"')));
      expect(texte, contains('%22'));
      expect(texte, contains('%0D%0A'));

      // Le texte injecté réapparaît, mais inerte : ses retours à la ligne
      // sont échappés, donc il reste la valeur d'un `filename`. Ce qui
      // compte est le nombre de *vraies* lignes d'en-tête, c'est-à-dire
      // celles qui suivent un CRLF réel.
      const ligneEntete = '\r\nContent-Disposition: form-data';
      expect(ligneEntete.allMatches(texte).length, 1);
    });

    test('garde les octets du fichier intacts', () {
      // Un JPEG commence par FF D8 FF : passer par une chaîne les
      // abîmerait silencieusement, et la photo arriverait corrompue.
      final brut = Uint8List.fromList([0xFF, 0xD8, 0xFF, 0x00, 0x1A, 0xFE]);
      final body = encodeMultipart(files: [
        UploadFile(field: 'images', filename: 'p.jpg', bytes: brut),
      ]);

      var trouve = false;
      for (var i = 0; i + brut.length <= body.bytes.length; i++) {
        final tranche = body.bytes.sublist(i, i + brut.length);
        if (tranche.toString() == brut.toString()) {
          trouve = true;
          break;
        }
      }
      expect(trouve, isTrue, reason: 'les octets du fichier ont été altérés');
    });

    test('nomme « fichier » une pièce sans nom', () {
      final body = encodeMultipart(files: [
        UploadFile(field: 'images', filename: '', bytes: octets('z')),
      ]);
      expect(utf8.decode(body.bytes), contains('filename="fichier"'));
    });
  });
}
