import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/models/message.dart';
import '../../core/network/api_exception.dart';
import '../../core/network/wrapped_multipart.dart';
import 'messaging_repository.dart';

class ThreadState {
  const ThreadState({
    this.messages = const [],
    this.loading = true,
    this.error,
    this.sending = false,
    this.echo,
    this.uploadProgress,
  });

  final List<Message> messages;
  final bool loading;
  final String? error;
  final bool sending;

  /// Le texte déjà tape, montre avant que le serveur l'ait confirme.
  final String? echo;

  /// 0 a 1 pendant un envoi de photos, null sinon.
  final double? uploadProgress;

  ThreadState copyWith({
    List<Message>? messages,
    bool? loading,
    Object? error = _keep,
    bool? sending,
    Object? echo = _keep,
    Object? uploadProgress = _keep,
  }) {
    return ThreadState(
      messages: messages ?? this.messages,
      loading: loading ?? this.loading,
      error: error == _keep ? this.error : error as String?,
      sending: sending ?? this.sending,
      echo: echo == _keep ? this.echo : echo as String?,
      uploadProgress:
          uploadProgress == _keep ? this.uploadProgress : uploadProgress as double?,
    );
  }

  static const _keep = Object();
}

/// Un fil ouvert : charge, se rafraichit, envoie.
class ThreadController extends StateNotifier<ThreadState> {
  ThreadController(this._repository, this._conversationId)
      : super(const ThreadState()) {
    _load(first: true);
    // Quatre secondes, comme sur le site. Channels a ete retiré du
    // projet : il n'y a pas de poussee serveur a attendre ici.
    _timer = Timer.periodic(const Duration(seconds: 4), (_) => _load());
  }

  final MessagingRepository _repository;
  final int _conversationId;
  Timer? _timer;

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  Future<void> _load({bool first = false}) async {
    try {
      final page = await _repository.messages(_conversationId);
      if (!mounted) return;
      // L'API pagine du plus recent au plus ancien ou l'inverse selon le
      // tri du modele : on ordonne ici, une fois, plutot que de s'en
      // remettre a l'ordre recu.
      final ordered = [...page.results]
        ..sort((a, b) => a.createdAt.compareTo(b.createdAt));
      state = state.copyWith(messages: ordered, loading: false, error: null);
      if (first) unawaited(_markRead());
    } on ApiException catch (error) {
      if (!mounted) return;
      // Une erreur pendant le rafraichissement ne doit pas effacer ce qui
      // est déjà lisible a l'ecran.
      state = state.copyWith(
        loading: false,
        error: state.messages.isEmpty ? error.message : null,
      );
    }
  }

  Future<void> _markRead() async {
    try {
      await _repository.markRead(_conversationId);
    } on ApiException {
      // Sans consequence : le fil se remarquera lu au prochain passage.
    }
  }

  Future<void> reload() => _load(first: true);

  /// Le dernier message a moi que l'ecran connait.
  int _lastMineId() => state.messages
      .where((m) => m.isMine)
      .fold(0, (highest, m) => m.id > highest ? m.id : highest);

  /// Un message a moi plus recent que [id] est-il arrive malgre l'erreur ?
  ///
  /// Une erreur ne prouve pas que rien n'est parti : le serveur peut avoir
  /// enregistre le message puis echoue sur la suite, ou la connexion
  /// s'etre coupee pendant la reponse. Afficher l'echec invitait alors a
  /// renvoyer, donc a doubler le message. On relit le fil pour trancher.
  /// Les identifiants, pas les heures : l'horloge du telephone et celle du
  /// serveur ne s'accordent pas toujours.
  Future<int?> _arrivedAfter(int id) async {
    try {
      final page = await _repository.messages(_conversationId);
      final mine = page.results.where((m) => m.isMine && m.id > id).map((m) => m.id);
      return mine.isEmpty ? null : mine.reduce((a, b) => a > b ? a : b);
    } on ApiException {
      return null;
    }
  }

  Future<bool> sendText(String body) async {
    final text = body.trim();
    if (text.isEmpty) return false;

    // Le champ se vide tout de suite et le texte passe dans l'echo : on
    // ne retape pas un message parce que le réseau a mis deux secondes.
    state = state.copyWith(sending: true, echo: text, error: null);
    final before = _lastMineId();
    try {
      try {
        await _repository.sendText(_conversationId, text);
      } on ApiException {
        if (await _arrivedAfter(before) == null) rethrow;
      }
      await _load();
      if (mounted) state = state.copyWith(sending: false, echo: null);
      return true;
    } on ApiException catch (error) {
      if (mounted) {
        state = state.copyWith(sending: false, echo: null, error: error.message);
      }
      return false;
    }
  }

  Future<bool> sendImages(List<UploadFile> images) async {
    if (images.isEmpty) return false;
    state = state.copyWith(sending: true, uploadProgress: 0, error: null);
    try {
      // Une photo par requete. Six photos dans un seul envoi depassaient a
      // coup sur la limite de duree de l'hebergeur sur un reseau mobile,
      // et la coupure les perdait toutes ; une par une, chacune tient, et
      // celles deja parties restent parties.
      var lastMine = _lastMineId();
      for (var index = 0; index < images.length; index++) {
        try {
          final sent = await _repository.sendImages(
            _conversationId,
            [images[index]],
            onProgress: (sent, total) {
              if (!mounted || total <= 0) return;
              state = state.copyWith(
                uploadProgress: (index + sent / total) / images.length,
              );
            },
          );
          lastMine = sent.id;
        } on ApiException {
          final arrived = await _arrivedAfter(lastMine);
          if (arrived == null) rethrow;
          lastMine = arrived;
        }
      }
      await _load();
      if (mounted) state = state.copyWith(sending: false, uploadProgress: null);
      return true;
    } on ApiException catch (error) {
      if (mounted) {
        state = state.copyWith(
          sending: false,
          uploadProgress: null,
          error: error.message,
        );
      }
      return false;
    }
  }

  Future<bool> sendAudio(UploadFile audio, int seconds) async {
    state = state.copyWith(sending: true, uploadProgress: 0, error: null);
    final before = _lastMineId();
    try {
      try {
        await _repository.sendAudio(
          _conversationId,
          audio,
          seconds,
          onProgress: (sent, total) {
            if (!mounted || total <= 0) return;
            state = state.copyWith(uploadProgress: sent / total);
          },
        );
      } on ApiException {
        if (await _arrivedAfter(before) == null) rethrow;
      }
      await _load();
      if (mounted) state = state.copyWith(sending: false, uploadProgress: null);
      return true;
    } on ApiException catch (error) {
      if (mounted) {
        state = state.copyWith(sending: false, uploadProgress: null, error: error.message);
      }
      return false;
    }
  }

  void clearError() {
    if (mounted) state = state.copyWith(error: null);
  }
}

final threadProvider =
    StateNotifierProvider.family.autoDispose<ThreadController, ThreadState, int>(
  (ref, conversationId) =>
      ThreadController(ref.watch(messagingRepositoryProvider), conversationId),
);
