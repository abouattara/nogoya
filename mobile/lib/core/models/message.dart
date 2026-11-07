import 'paginated.dart';
import 'product.dart';
import 'user.dart';

enum AttachmentKind { image, video, audio }

/// Un fichier joint a un message.
///
/// `url` pointe vers l'API, jamais vers le stockage : une conversation est
/// privee, et un lien de bucket reste lisible par quiconque l'obtient.
/// L'appartenance est revérifiée a chaque requete, ce qui veut dire que
/// l'application doit charger ces fichiers avec son jeton.
class MessageAttachment {
  const MessageAttachment({
    required this.id,
    required this.kind,
    required this.status,
    required this.url,
    required this.posterUrl,
    required this.width,
    required this.height,
    required this.duration,
  });

  final int id;
  final AttachmentKind kind;
  final String status;
  final String url;
  final String? posterUrl;
  final int width;
  final int height;
  final int duration;

  bool get isReady => status == 'ready';

  factory MessageAttachment.fromJson(Map<String, dynamic> json) {
    return MessageAttachment(
      id: json.intOf('id'),
      kind: switch (json.str('kind')) {
        'video' => AttachmentKind.video,
        'audio' => AttachmentKind.audio,
        _ => AttachmentKind.image,
      },
      status: json.str('status', 'ready'),
      url: json.str('url'),
      posterUrl: json.strOrNull('poster_url'),
      width: json.intOf('width'),
      height: json.intOf('height'),
      duration: json.intOf('duration'),
    );
  }
}

class Message {
  const Message({
    required this.id,
    required this.conversationId,
    required this.sender,
    required this.type,
    required this.body,
    required this.attachments,
    required this.sharedProduct,
    required this.createdAt,
    required this.readAt,
    required this.isMine,
  });

  final int id;
  final int conversationId;
  final PublicUser sender;
  final String type;
  final String body;
  final List<MessageAttachment> attachments;
  final Product? sharedProduct;
  final DateTime createdAt;
  final DateTime? readAt;

  /// Calcule par le serveur, pas par l'application.
  ///
  /// L'équipe répond au nom du compte de service : comparer l'expediteur a
  /// l'utilisateur courant rendait, cote équipe, tous les messages « pas
  /// de moi » et affichait la conversation d'une seule couleur. Le serveur
  /// sait sous quelle identite chacun ecrit ; on lui fait confiance.
  final bool isMine;

  /// Une note de service n'appartient a personne.
  bool get isSystemNote => type == 'system';

  factory Message.fromJson(Map<String, dynamic> json) {
    final product = json.mapOf('shared_product');
    return Message(
      id: json.intOf('id'),
      conversationId: json.intOf('conversation'),
      sender: PublicUser.fromJson(json.mapOf('sender') ?? const {}),
      type: json.str('message_type', 'text'),
      body: json.str('body'),
      attachments: json.listOf('attachments').map(MessageAttachment.fromJson).toList(),
      sharedProduct: product == null ? null : Product.fromJson(product),
      createdAt: json.dateOf('created_at') ?? DateTime.now(),
      readAt: json.dateOf('read_at'),
      isMine: json.boolOf('is_mine'),
    );
  }
}

/// Un fil, vu depuis la liste des conversations.
class Conversation {
  const Conversation({
    required this.id,
    required this.other,
    required this.lastBody,
    required this.lastAt,
    required this.lastIsMine,
    required this.unreadCount,
    required this.updatedAt,
  });

  final int id;

  /// Qui est en face. Pour un membre, c'est toujours NOGOYA : c'est la
  /// promesse du schema intermediaire, et le serveur la tient.
  final PublicUser other;

  final String? lastBody;
  final DateTime? lastAt;
  final bool lastIsMine;
  final int unreadCount;
  final DateTime? updatedAt;

  bool get hasUnread => unreadCount > 0;

  factory Conversation.fromJson(Map<String, dynamic> json) {
    final last = json.mapOf('last_message');
    return Conversation(
      id: json.intOf('id'),
      other: PublicUser.fromJson(json.mapOf('other_participant') ?? const {}),
      lastBody: last?.strOrNull('body'),
      lastAt: last?.dateOf('created_at'),
      lastIsMine: last?.boolOf('is_mine') ?? false,
      unreadCount: json.intOf('unread_count'),
      updatedAt: json.dateOf('updated_at'),
    );
  }
}
