import 'package:binogoya/core/models/message.dart';
import 'package:binogoya/core/models/paginated.dart';
import 'package:binogoya/core/models/user.dart';
import 'package:binogoya/core/network/api_exception.dart';
import 'package:binogoya/features/messaging/messaging_repository.dart';
import 'package:binogoya/features/messaging/thread_controller.dart';
import 'package:flutter_test/flutter_test.dart';

Message mine(int id) => Message(
      id: id,
      conversationId: 1,
      sender: const PublicUser(id: 1, fullName: 'Moi', avatar: null),
      type: 'text',
      body: 'm$id',
      attachments: const [],
      sharedProduct: null,
      createdAt: DateTime(2026, 11, 17, 10, id),
      readAt: null,
      isMine: true,
    );

/// Un faux depot : l'envoi echoue toujours, et le fil contient ce qu'on veut.
class _Repo implements MessagingRepository {
  _Repo(this.thread);

  List<Message> thread;

  @override
  Future<Paginated<Message>> messages(int conversationId, {int page = 1}) async =>
      Paginated(count: thread.length, results: thread);

  @override
  Future<Message> sendText(int conversationId, String body) async =>
      throw ApiException('Une erreur est survenue.', statusCode: 500);

  @override
  Future<void> markRead(int conversationId) async {}

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

void main() {
  test("une erreur alors que le message est bien arrivé n'est pas un échec", () async {
    // Le serveur enregistrait le message puis répondait 500 : l'écran
    // affichait l'échec, et on renvoyait le même message.
    final repo = _Repo([mine(1)]);
    final controller = ThreadController(repo, 1);
    await Future<void>.delayed(Duration.zero);

    repo.thread = [mine(1), mine(2)]; // le message est arrivé malgré l'erreur
    final ok = await controller.sendText('Bonjour');

    expect(ok, isTrue);
    expect(controller.state.error, isNull);
    controller.dispose();
  });

  test("une erreur sans message arrivé reste une erreur", () async {
    final repo = _Repo([mine(1)]);
    final controller = ThreadController(repo, 1);
    await Future<void>.delayed(Duration.zero);

    final ok = await controller.sendText('Bonjour');

    expect(ok, isFalse);
    expect(controller.state.error, isNotNull);
    controller.dispose();
  });
}
