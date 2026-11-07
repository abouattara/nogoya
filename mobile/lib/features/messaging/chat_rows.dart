import '../../core/models/message.dart';

/// Un repere de journee, ou un message avec sa place dans une serie.
sealed class ChatRow {
  const ChatRow();
}

class DayRow extends ChatRow {
  const DayRow(this.date);
  final DateTime date;
}

class MessageRow extends ChatRow {
  const MessageRow({
    required this.message,
    required this.grouped,
    required this.endsGroup,
  });

  final Message message;

  /// Suit un message du meme auteur, a quelques minutes pres.
  final bool grouped;

  /// Dernier d'une serie : porte l'heure et le coin carre.
  final bool endsGroup;
}

/// Deux messages se collent-ils en un seul bloc ?
///
/// Cinq minutes : au-dela, l'interlocuteur est reparti et revenu, et
/// coller les bulles ferait perdre cette respiration.
bool sameGroup(Message? previous, Message current) {
  if (previous == null) return false;
  if (previous.isMine != current.isMine) return false;
  final gap = current.createdAt.difference(previous.createdAt);
  return !gap.isNegative && gap.inMinutes < 5;
}

bool _sameDay(DateTime a, DateTime b) =>
    a.year == b.year && a.month == b.month && a.day == b.day;

/// Decoupe un fil en journees et en series.
///
/// Le calcul vit ici, hors du rendu : une bulle ne peut pas savoir
/// qu'elle termine une serie sans regarder la suivante, et lui passer
/// toute la liste la rendrait dependante de l'ordre d'affichage. Mis a
/// part, le decoupage se teste sans monter d'ecran.
///
/// `messages` est attendu du plus ancien au plus recent.
List<ChatRow> buildChatRows(List<Message> messages) {
  final rows = <ChatRow>[];

  for (var index = 0; index < messages.length; index++) {
    final message = messages[index];
    final previous = index == 0 ? null : messages[index - 1];
    final next = index + 1 < messages.length ? messages[index + 1] : null;

    final newDay = previous == null || !_sameDay(previous.createdAt, message.createdAt);
    if (newDay) rows.add(DayRow(message.createdAt));

    // Une note de service ne se groupe avec rien : elle n'a pas d'auteur.
    final isNote = message.isSystemNote;
    final grouped = !newDay &&
        !isNote &&
        !previous.isSystemNote &&
        sameGroup(previous, message);
    final endsGroup = isNote ||
        next == null ||
        next.isSystemNote ||
        !_sameDay(next.createdAt, message.createdAt) ||
        !sameGroup(message, next);

    rows.add(MessageRow(message: message, grouped: grouped, endsGroup: endsGroup));
  }

  return rows;
}
