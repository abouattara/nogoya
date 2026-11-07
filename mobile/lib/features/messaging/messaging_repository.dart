import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/models/message.dart';
import '../../core/models/paginated.dart';
import '../../core/network/api_client.dart';
import '../../core/providers.dart';

class MessagingRepository {
  MessagingRepository(this._api);

  final ApiClient _api;

  Future<Paginated<Conversation>> conversations({int page = 1}) async {
    final data = await _api.get<Map<String, dynamic>>(
      '/conversations/',
      query: {'page': page},
    );
    return Paginated.fromJson(data, Conversation.fromJson);
  }

  Future<Paginated<Message>> messages(int conversationId, {int page = 1}) async {
    final data = await _api.get<Map<String, dynamic>>(
      '/conversations/$conversationId/messages/',
      query: {'page': page},
    );
    return Paginated.fromJson(data, Message.fromJson);
  }

  Future<Message> sendText(int conversationId, String body) async {
    final data = await _api.post<Map<String, dynamic>>(
      '/conversations/$conversationId/messages/',
      data: {'body': body},
    );
    return Message.fromJson(data);
  }

  /// Envoie des photos, une requete par lot, avec la progression.
  ///
  /// Les octets partent en multipart comme depuis le site. Le serveur
  /// accepte plusieurs `images` par message : les grouper evite un fil
  /// ou six photos deviennent six bulles.
  Future<Message> sendImages(
    int conversationId,
    List<MultipartFile> images, {
    String body = '',
    void Function(int sent, int total)? onProgress,
  }) async {
    final form = FormData();
    if (body.isNotEmpty) form.fields.add(MapEntry('body', body));
    for (final image in images) {
      form.files.add(MapEntry('images', image));
    }
    final data = await _api.upload<Map<String, dynamic>>(
      '/conversations/$conversationId/messages/',
      form,
      onProgress: onProgress,
    );
    return Message.fromJson(data);
  }

  Future<void> markRead(int conversationId) async {
    await _api.post<dynamic>('/conversations/$conversationId/read/');
  }

  Future<int> unreadCount() async {
    final data = await _api.get<Map<String, dynamic>>('/conversations/unread-count/');
    return data.intOf('unread_count');
  }

  /// Ouvre ou retrouve le fil lie a un bien.
  ///
  /// Un membre n'a qu'un seul fil avec NOGOYA : le serveur renvoie le fil
  /// existant plutot que d'en créer un par bien, ce qui evitait d'avoir
  /// dix conversations avec la meme personne.
  Future<Conversation> openForProduct(int productId) async {
    final data = await _api.post<Map<String, dynamic>>(
      '/conversations/',
      data: {'product': productId},
    );
    return Conversation.fromJson(data);
  }
}

final messagingRepositoryProvider = Provider<MessagingRepository>((ref) {
  return MessagingRepository(ref.watch(apiClientProvider));
});

/// Le compteur global, rafraichi doucement.
///
/// Quinze secondes comme sur le site : assez pour qu'une pastille
/// apparaisse sans qu'on la guette, assez peu pour ne pas vider la
/// batterie ni le forfait.
final unreadCountProvider = StreamProvider.autoDispose<int>((ref) async* {
  final repository = ref.watch(messagingRepositoryProvider);
  while (true) {
    try {
      yield await repository.unreadCount();
    } on Exception {
      // Reseau coupe : on garde le dernier compte connu plutot que
      // d'afficher zero, qui ferait croire qu'un message a ete lu.
    }
    await Future<void>.delayed(const Duration(seconds: 15));
  }
});
