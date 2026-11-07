import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/format.dart';
import '../../core/models/message.dart';
import '../../core/models/paginated.dart';
import '../../core/theme/app_colors.dart';
import '../../shared/widgets/avatar.dart';
import '../../shared/widgets/states.dart';
import '../auth/session_controller.dart';
import 'messaging_repository.dart';

final conversationsProvider =
    FutureProvider.autoDispose<Paginated<Conversation>>((ref) {
  return ref.watch(messagingRepositoryProvider).conversations();
});

class ConversationsScreen extends ConsumerWidget {
  const ConversationsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final session = ref.watch(sessionProvider);

    if (!session.isSignedIn) {
      return Scaffold(
        appBar: AppBar(title: const Text('Messages')),
        body: EmptyView(
          icon: Icons.forum_outlined,
          title: 'Connectez-vous pour echanger',
          description:
              "Vos echanges avec l'équipe BINOGOYA tiennent dans un seul fil, "
              'une fois votre compte créé.',
          action: FilledButton(
            onPressed: () => context.push('/connexion'),
            child: const Text('Se connecter'),
          ),
        ),
      );
    }

    final conversations = ref.watch(conversationsProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Messages')),
      body: conversations.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => ErrorView(
          message: '$error'.replaceFirst('ApiException: ', ''),
          onRetry: () => ref.invalidate(conversationsProvider),
        ),
        data: (page) {
          if (page.results.isEmpty) {
            return const EmptyView(
              icon: Icons.forum_outlined,
              title: 'Aucune conversation',
              description:
                  "Faites une demande depuis un bien : l'équipe BINOGOYA "
                  'vous répond ici.',
            );
          }
          return RefreshIndicator(
            onRefresh: () async => ref.invalidate(conversationsProvider),
            child: ListView.separated(
              itemCount: page.results.length,
              separatorBuilder: (_, _) => const Divider(height: 1, indent: 72),
              itemBuilder: (context, index) {
                final conversation = page.results[index];
                return _ConversationTile(conversation: conversation);
              },
            ),
          );
        },
      ),
    );
  }
}

class _ConversationTile extends StatelessWidget {
  const _ConversationTile({required this.conversation});

  final Conversation conversation;

  @override
  Widget build(BuildContext context) {
    final unread = conversation.hasUnread;
    final preview = conversation.lastBody == null
        ? 'Nouvelle conversation'
        : '${conversation.lastIsMine ? 'Vous : ' : ''}${conversation.lastBody}';

    return ListTile(
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
      leading: Avatar(name: conversation.other.fullName, url: conversation.other.avatar),
      title: Row(
        children: [
          Expanded(
            child: Text(
              conversation.other.fullName,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                fontWeight: unread ? FontWeight.w700 : FontWeight.w500,
              ),
            ),
          ),
          if (conversation.lastAt != null)
            Text(
              Fmt.relative(conversation.lastAt!),
              style: const TextStyle(fontSize: 11, color: AppColors.foregroundMuted),
            ),
        ],
      ),
      subtitle: Padding(
        padding: const EdgeInsets.only(top: 2),
        child: Row(
          children: [
            Expanded(
              child: Text(
                preview,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  fontSize: 13,
                  color: unread ? AppColors.foreground : AppColors.foregroundMuted,
                ),
              ),
            ),
            if (unread)
              Container(
                margin: const EdgeInsets.only(left: 8),
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: AppColors.brand600,
                  borderRadius: BorderRadius.circular(999),
                ),
                child: Text(
                  '${conversation.unreadCount}',
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 11,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
          ],
        ),
      ),
      onTap: () => context.push('/messages/${conversation.id}'),
    );
  }
}
