import 'package:dio/dio.dart';

/// Une erreur d'API, déjà traduite.
///
/// L'ecran ne doit jamais avoir a lire un `DioException` ni a deviner ce
/// que veut dire un 409. La traduction se fait une fois, ici, et chaque
/// ecran se contente d'afficher `message` et, s'il en a besoin, de
/// repartir les `fieldErrors` sur ses champs.
class ApiException implements Exception {
  ApiException(this.message, {this.statusCode, this.fieldErrors = const {}});

  final String message;
  final int? statusCode;

  /// Les erreurs champ par champ renvoyees par DRF : `{champ: [messages]}`.
  final Map<String, List<String>> fieldErrors;

  bool get isUnauthorized => statusCode == 401;
  bool get isForbidden => statusCode == 403;
  bool get isNotFound => statusCode == 404;

  /// Le serveur demande une demande de location avant de donner un contact.
  bool get needsRentalRequest => statusCode == 409;

  @override
  String toString() => 'ApiException($statusCode): $message';

  /// Traduit ce que Dio a rapporte.
  ///
  /// Le réseau burkinabe coupe souvent : la difference entre « pas de
  /// réseau » et « le serveur a refuse » décide de ce que la personne doit
  /// faire, et les confondre sous un « une erreur est survenue » la laisse
  /// sans recours.
  factory ApiException.from(DioException error) {
    final status = error.response?.statusCode;

    switch (error.type) {
      case DioExceptionType.connectionTimeout:
      case DioExceptionType.sendTimeout:
      case DioExceptionType.receiveTimeout:
        return ApiException(
          'La connexion est trop lente. Réessayez dans un instant.',
          statusCode: status,
        );
      case DioExceptionType.connectionError:
        return ApiException(
          "Impossible de joindre BINOGOYA. Vérifiez votre connexion.",
          statusCode: status,
        );
      case DioExceptionType.cancel:
        return ApiException('Demande annulée.', statusCode: status);
      default:
        break;
    }

    final fields = _readFieldErrors(error.response?.data);
    final detail = _readDetail(error.response?.data);

    return ApiException(
      detail ?? _messageForStatus(status, fields),
      statusCode: status,
      fieldErrors: fields,
    );
  }

  static String _messageForStatus(int? status, Map<String, List<String>> fields) {
    if (fields.isNotEmpty) {
      return fields.values.expand((messages) => messages).join(' ');
    }
    if (status != null && status >= 500) {
      return 'BINOGOYA rencontre un problème. Réessayez plus tard.';
    }
    return switch (status) {
      400 => 'Les informations envoyées ne sont pas valides.',
      401 => 'Votre session a expiré. Reconnectez-vous.',
      403 => "Vous n'avez pas les droits pour cette action.",
      404 => 'Introuvable.',
      // Le serveur ne dit jamais si une chose existe hors de votre
      // perimetre : un 404 et un « pas a vous » se ressemblent, par choix.
      429 => 'Trop de tentatives. Patientez une minute.',
      _ => 'Une erreur est survenue.',
    };
  }

  static String? _readDetail(Object? data) {
    if (data is Map && data['detail'] is String) return data['detail'] as String;
    return null;
  }

  static Map<String, List<String>> _readFieldErrors(Object? data) {
    if (data is! Map) return const {};
    final result = <String, List<String>>{};
    data.forEach((key, value) {
      if (key == 'detail') return;
      if (value is List) {
        result['$key'] = value.map((item) => '$item').toList();
      } else if (value is String) {
        result['$key'] = [value];
      } else if (value is Map) {
        // Les erreurs d'attribut dynamique arrivent imbriquees :
        // {"attributes": {"marque": "« Marque » est obligatoire."}}
        value.forEach((inner, message) => result['$key.$inner'] = ['$message']);
      }
    });
    return result;
  }
}
