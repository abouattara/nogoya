import 'dart:async';

import 'package:dio/dio.dart';

import '../config/app_config.dart';
import '../storage/token_store.dart';
import 'api_exception.dart';

/// Le client HTTP de l'application, et la seule porte vers l'API.
///
/// Il porte trois choses qu'aucun ecran ne devrait refaire :
///
/// * le jeton d'acces sur chaque requete,
/// * le rafraichissement quand il expiré, **une seule fois a la fois**,
/// * l'identifiant de visiteur, sans lequel chaque appel compte comme une
///   personne nouvelle et fait exploser les compteurs de vues.
class ApiClient {
  ApiClient(this._tokens, {Dio? dio, Future<void> Function()? onSessionLost})
      : _onSessionLost = onSessionLost,
        _dio = dio ?? Dio() {
    _dio.options
      ..baseUrl = AppConfig.apiRoot
      ..connectTimeout = const Duration(seconds: 15)
      // Genereux : un fil de discussion avec des photos part sur un réseau
      // qui n'a pas toujours la 4G.
      ..receiveTimeout = const Duration(seconds: 40)
      ..sendTimeout = const Duration(seconds: 60)
      ..headers['Accept'] = 'application/json'
      // DRF choisit la langue des messages d'erreur la-dessus ; sans cet
      // en-tete, un téléphone en anglais recevait « This field is
      // required » au milieu d'une interface francaise.
      ..headers['Accept-Language'] = 'fr';

    _dio.interceptors.add(
      InterceptorsWrapper(onRequest: _onRequest, onError: _onError),
    );
  }

  final Dio _dio;
  final TokenStore _tokens;
  final Future<void> Function()? _onSessionLost;

  /// Le rafraichissement en cours, s'il y en a un.
  ///
  /// Quand quatre appels partent ensemble au reveil de l'application et
  /// reviennent tous en 401, un seul rafraichissement doit avoir lieu :
  /// la rotation des jetons du serveur invalide l'ancien refresh, et
  /// quatre echanges simultanes en invalideraient trois pour rien, donc
  /// deconnecteraient la personne.
  Future<String?>? _refreshing;

  Dio get dio => _dio;

  void _onRequest(RequestOptions options, RequestInterceptorHandler handler) {
    final access = _tokens.accessToken;
    if (access != null) {
      options.headers['Authorization'] = 'Bearer $access';
    }
    options.headers['X-Visitor-Id'] = _tokens.visitorId();
    handler.next(options);
  }

  Future<void> _onError(DioException error, ErrorInterceptorHandler handler) async {
    final isExpired = error.response?.statusCode == 401;
    final path = error.requestOptions.path;
    // Un 401 sur la connexion ou le rafraichissement lui-meme n'est pas un
    // jeton perime : c'est un refus. Réessayer bouclerait.
    final isAuthCall = path.contains('/auth/login') || path.contains('/auth/refresh');

    if (!isExpired || isAuthCall || error.requestOptions.extra['retried'] == true) {
      return handler.next(error);
    }

    final token = await _refreshAccessToken();
    if (token == null) {
      await _onSessionLost?.call();
      return handler.next(error);
    }

    try {
      final options = error.requestOptions;
      options.extra['retried'] = true;
      options.headers['Authorization'] = 'Bearer $token';
      final response = await _dio.fetch<dynamic>(options);
      return handler.resolve(response);
    } on DioException catch (retryError) {
      return handler.next(retryError);
    }
  }

  Future<String?> _refreshAccessToken() {
    return _refreshing ??= _doRefresh().whenComplete(() => _refreshing = null);
  }

  Future<String?> _doRefresh() async {
    final refresh = await _tokens.readRefreshToken();
    if (refresh == null) return null;

    try {
      // Un Dio nu : passer par `_dio` relancerait l'intercepteur et, sur
      // un refresh perime, rappellerait ce meme code.
      final response = await Dio(
        BaseOptions(baseUrl: AppConfig.apiRoot, headers: {'Accept': 'application/json'}),
      ).post<Map<String, dynamic>>(
        '/auth/refresh/',
        data: {'refresh': refresh},
      );

      final data = response.data ?? const {};
      final access = data['access'] as String?;
      if (access == null) return null;
      _tokens.setAccessToken(access);

      // Le serveur fait tourner les refresh et met l'ancien sur liste
      // noire. Ne pas garder le nouveau condamnerait la session a la
      // prochaine expiration.
      final rotated = data['refresh'] as String?;
      if (rotated != null) await _tokens.saveRefreshToken(rotated);
      return access;
    } on DioException {
      await _tokens.clear();
      return null;
    }
  }

  // --- verbes ---------------------------------------------------------

  Future<T> get<T>(String path, {Map<String, dynamic>? query}) {
    return _run(() => _dio.get<T>(path, queryParameters: query));
  }

  Future<T> post<T>(String path, {Object? data, Map<String, dynamic>? query}) {
    return _run(() => _dio.post<T>(path, data: data, queryParameters: query));
  }

  Future<T> patch<T>(String path, {Object? data}) {
    return _run(() => _dio.patch<T>(path, data: data));
  }

  Future<T> delete<T>(String path) {
    return _run(() => _dio.delete<T>(path));
  }

  Future<T> upload<T>(
    String path,
    FormData form, {
    void Function(int sent, int total)? onProgress,
  }) {
    return _run(
      () => _dio.post<T>(path, data: form, onSendProgress: onProgress),
    );
  }

  Future<T> _run<T>(Future<Response<T>> Function() call) async {
    try {
      final response = await call();
      return response.data as T;
    } on DioException catch (error) {
      throw ApiException.from(error);
    }
  }
}
