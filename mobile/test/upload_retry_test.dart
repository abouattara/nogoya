import 'dart:convert';
import 'dart:typed_data';

import 'package:binogoya/core/network/wrapped_multipart.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';

/// Un faux serveur qui note chaque corps reçu, sans réseau.
class _Recorder implements HttpClientAdapter {
  final bodies = <List<int>>[];

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    final bytes = <int>[];
    if (requestStream != null) {
      await for (final chunk in requestStream) {
        bytes.addAll(chunk);
      }
    }
    bodies.add(bytes);
    return ResponseBody.fromString(
      jsonEncode({'ok': true}),
      201,
      headers: {
        Headers.contentTypeHeader: ['application/json'],
      },
    );
  }

  @override
  void close({bool force = false}) {}
}

void main() {
  test("un envoi relancé repart avec son corps complet", () async {
    // L'intercepteur relance la requête quand le jeton expire en plein
    // envoi, avec les mêmes `RequestOptions`. La relance doit repartir avec
    // le corps entier : ce test garde contre un passage à un flux qui ne
    // se relirait pas.
    final recorder = _Recorder();
    final dio = Dio()..httpClientAdapter = recorder;
    final body = encodeMultipart(files: [
      UploadFile(
        field: 'images',
        filename: 'photo.jpg',
        bytes: Uint8List.fromList(List.generate(5000, (i) => i % 256)),
        contentType: 'image/jpeg',
      ),
    ]);

    final response = await dio.post<dynamic>(
      'https://exemple.test/messages/',
      data: body.bytes,
      options: Options(headers: body.headers),
    );
    // Ce que fait l'intercepteur après un 401 : refetch des mêmes options.
    await dio.fetch<dynamic>(response.requestOptions);

    expect(recorder.bodies, hasLength(2));
    expect(recorder.bodies[0], body.bytes);
    expect(recorder.bodies[1], body.bytes, reason: 'la seconde tentative est partie amputée');
  });

  test("l'envoi garde l'étiquette octet-stream et sa frontière", () async {
    // Sans cela, le serveur ne sait pas relire le corps enveloppé.
    final recorder = _Recorder();
    final dio = Dio()..httpClientAdapter = recorder;
    final body = encodeMultipart(fields: {'durations': '4'});

    final response = await dio.post<dynamic>(
      'https://exemple.test/messages/',
      data: body.bytes,
      options: Options(headers: body.headers),
    );

    final headers = response.requestOptions.headers;
    expect(headers['Content-Type'] ?? headers['content-type'], 'application/octet-stream');
    expect(headers['X-Upload-Boundary'], body.boundary);
  });
}
