import 'package:cached_network_image/cached_network_image.dart';
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';

import '../../core/format.dart';
import '../../core/models/message.dart';
import '../../core/providers.dart';
import '../../core/theme/app_colors.dart';
import '../../shared/widgets/avatar.dart';
import '../../shared/widgets/states.dart';
import 'chat_rows.dart';
import 'thread_controller.dart';

/// Un fil de discussion avec l'équipe BINOGOYA.
class ThreadScreen extends ConsumerStatefulWidget {
  const ThreadScreen({super.key, required this.conversationId});

  final int conversationId;

  @override
  ConsumerState<ThreadScreen> createState() => _ThreadScreenState();
}

class _ThreadScreenState extends ConsumerState<ThreadScreen> {
  final _input = TextEditingController();
  final _scroll = ScrollController();
  bool _stickToBottom = true;

  @override
  void initState() {
    super.initState();
    _scroll.addListener(() {
      if (!_scroll.hasClients) return;
      // On suit le bas du fil, sauf si le lecteur est remonte : tirer la
      // liste sous ses yeux pendant qu'il relit est insupportable.
      _stickToBottom = _scroll.position.pixels >=
          _scroll.position.maxScrollExtent - 120;
    });
  }

  @override
  void dispose() {
    _input.dispose();
    _scroll.dispose();
    super.dispose();
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!_scroll.hasClients || !_stickToBottom) return;
      _scroll.jumpTo(_scroll.position.maxScrollExtent);
    });
  }

  Future<void> _send() async {
    final text = _input.text;
    if (text.trim().isEmpty) return;
    _input.clear();
    _stickToBottom = true;
    final sent = await ref.read(threadProvider(widget.conversationId).notifier).sendText(text);
    if (!sent && mounted) {
      // L'envoi a echoue : le texte revient dans le champ, il n'est pas perdu.
      _input.text = text;
    }
  }

  Future<void> _pickImages() async {
    final picked = await ImagePicker().pickMultiImage(
      // Le téléphone compresse avant l'envoi : les fichiers bruts de 12 Mpx
      // faisaient echouer la requete cote serveur sur le site, et le
      // réseau d'ici ne les supporterait pas davantage.
      maxWidth: 1600,
      maxHeight: 1600,
      imageQuality: 82,
      limit: 6,
    );
    if (picked.isEmpty) return;

    final files = <MultipartFile>[];
    for (final image in picked) {
      files.add(
        await MultipartFile.fromFile(image.path, filename: image.name),
      );
    }
    _stickToBottom = true;
    await ref.read(threadProvider(widget.conversationId).notifier).sendImages(files);
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(threadProvider(widget.conversationId));
    final rows = buildChatRows(state.messages);

    ref.listen(threadProvider(widget.conversationId), (previous, next) {
      if (previous?.messages.length != next.messages.length) _scrollToBottom();
      if (next.error != null && previous?.error != next.error) {
        ScaffoldMessenger.of(context)
          ..clearSnackBars()
          ..showSnackBar(SnackBar(content: Text(next.error!)));
        ref.read(threadProvider(widget.conversationId).notifier).clearError();
      }
    });

    return Scaffold(
      appBar: AppBar(
        title: const Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('BINOGOYA'),
            Text(
              'Toutes vos demandes tiennent dans ce fil.',
              style: TextStyle(fontSize: 11, color: AppColors.foregroundMuted),
            ),
          ],
        ),
      ),
      body: Column(
        children: [
          Expanded(
            child: state.loading
                ? const Center(child: CircularProgressIndicator())
                : state.error != null && state.messages.isEmpty
                    ? ErrorView(
                        message: state.error!,
                        onRetry: () => ref
                            .read(threadProvider(widget.conversationId).notifier)
                            .reload(),
                      )
                    : rows.isEmpty && state.echo == null
                        ? const EmptyView(
                            icon: Icons.chat_bubble_outline,
                            title: 'Rien encore',
                            description:
                                "Écrivez votre premier message. L'équipe vérifie "
                                'la disponibilité avant de vous mettre en relation.',
                          )
                        : Container(
                            color: AppColors.surfaceMuted.withValues(alpha: 0.4),
                            child: ListView.builder(
                              controller: _scroll,
                              padding: const EdgeInsets.fromLTRB(12, 12, 12, 16),
                              itemCount: rows.length + (state.echo == null ? 0 : 1),
                              itemBuilder: (context, index) {
                                if (index >= rows.length) {
                                  return _EchoBubble(text: state.echo!);
                                }
                                return switch (rows[index]) {
                                  DayRow(:final date) => _DaySeparator(date: date),
                                  MessageRow(
                                    :final message,
                                    :final grouped,
                                    :final endsGroup
                                  ) =>
                                    _Bubble(
                                      message: message,
                                      grouped: grouped,
                                      endsGroup: endsGroup,
                                    ),
                                };
                              },
                            ),
                          ),
          ),
          if (state.uploadProgress != null)
            LinearProgressIndicator(value: state.uploadProgress),
          _Composer(
            controller: _input,
            sending: state.sending,
            onSend: _send,
            onPickImages: _pickImages,
          ),
        ],
      ),
    );
  }
}

class _DaySeparator extends StatelessWidget {
  const _DaySeparator({required this.date});

  final DateTime date;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 12),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 3),
        decoration: BoxDecoration(
          color: AppColors.surface,
          border: Border.all(color: AppColors.border),
          borderRadius: BorderRadius.circular(999),
        ),
        child: Text(
          Fmt.dayLabel(date),
          style: const TextStyle(fontSize: 11, color: AppColors.foregroundMuted),
        ),
      ),
    );
  }
}

class _Bubble extends ConsumerWidget {
  const _Bubble({
    required this.message,
    required this.grouped,
    required this.endsGroup,
  });

  final Message message;
  final bool grouped;
  final bool endsGroup;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    if (message.isSystemNote) return _SystemNote(message: message);

    final mine = message.isMine;
    final radius = BorderRadius.only(
      topLeft: const Radius.circular(16),
      topRight: const Radius.circular(16),
      bottomLeft: Radius.circular(endsGroup && !mine ? 6 : 16),
      bottomRight: Radius.circular(endsGroup && mine ? 6 : 16),
    );

    return Padding(
      padding: EdgeInsets.only(top: grouped ? 2 : 10),
      child: Row(
        mainAxisAlignment: mine ? MainAxisAlignment.end : MainAxisAlignment.start,
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          if (!mine)
            SizedBox(
              width: 28,
              child: endsGroup
                  ? Avatar(name: message.sender.fullName, url: message.sender.avatar, size: 28)
                  : null,
            ),
          if (!mine) const SizedBox(width: 8),
          Flexible(
            child: Column(
              crossAxisAlignment:
                  mine ? CrossAxisAlignment.end : CrossAxisAlignment.start,
              children: [
                Container(
                  constraints: BoxConstraints(
                    maxWidth: MediaQuery.sizeOf(context).width * 0.74,
                  ),
                  padding: message.attachments.isEmpty && message.body.isNotEmpty
                      ? const EdgeInsets.symmetric(horizontal: 12, vertical: 9)
                      : const EdgeInsets.all(4),
                  decoration: BoxDecoration(
                    color: mine ? AppColors.brand600 : AppColors.surface,
                    border: mine ? null : Border.all(color: AppColors.border),
                    borderRadius: radius,
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      if (message.attachments.isNotEmpty)
                        _Attachments(attachments: message.attachments),
                      if (message.body.isNotEmpty)
                        Padding(
                          padding: message.attachments.isEmpty
                              ? EdgeInsets.zero
                              : const EdgeInsets.fromLTRB(8, 6, 8, 4),
                          child: Text(
                            message.body,
                            style: TextStyle(
                              color: mine ? Colors.white : AppColors.foreground,
                              height: 1.35,
                            ),
                          ),
                        ),
                    ],
                  ),
                ),
                if (endsGroup)
                  Padding(
                    padding: const EdgeInsets.only(top: 2, left: 4, right: 4),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          Fmt.time(message.createdAt),
                          style: const TextStyle(
                            fontSize: 11,
                            color: AppColors.foregroundMuted,
                          ),
                        ),
                        if (mine && message.readAt != null) ...[
                          const SizedBox(width: 3),
                          const Icon(Icons.done_all, size: 13, color: AppColors.brand600),
                        ],
                      ],
                    ),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// Le recapitulatif d'une demande.
///
/// Ni de l'un ni de l'autre : centre et encadre, jamais aligne du cote du
/// client, qui croyait sinon l'avoir ecrit lui-meme.
class _SystemNote extends StatelessWidget {
  const _SystemNote({required this.message});

  final Message message;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 10),
      child: Center(
        child: Container(
          constraints: const BoxConstraints(maxWidth: 420),
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: AppColors.brand50,
            border: Border.all(color: AppColors.brand200),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'DEMANDE DE LOCATION',
                style: TextStyle(
                  fontSize: 10,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 0.6,
                  color: AppColors.brand700,
                ),
              ),
              const SizedBox(height: 6),
              if (message.body.isNotEmpty)
                Text(
                  message.body,
                  style: const TextStyle(
                    fontSize: 13,
                    height: 1.45,
                    color: AppColors.brand900,
                  ),
                ),
              if (message.sharedProduct != null) ...[
                const SizedBox(height: 8),
                InkWell(
                  onTap: () => context.push('/produits/${message.sharedProduct!.slug}'),
                  borderRadius: BorderRadius.circular(8),
                  child: Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: AppColors.surface,
                      border: Border.all(color: AppColors.border),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Row(
                      children: [
                        Expanded(
                          child: Text(
                            message.sharedProduct!.title,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                              fontWeight: FontWeight.w600,
                              fontSize: 13,
                              // Explicite : sans elle, la couleur serait
                              // heritee du conteneur, et le jour ou cette
                              // carte se pose dans une bulle indigo le
                              // titre disparaitrait sur fond blanc.
                              color: AppColors.foreground,
                            ),
                          ),
                        ),
                        const Icon(Icons.chevron_right, size: 18),
                      ],
                    ),
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

/// Les photos d'un message.
///
/// Chargees avec le jeton : une conversation est privee, les fichiers ne
/// sont pas servis par une URL de stockage, et l'API revérifie
/// l'appartenance a chaque requete.
class _Attachments extends ConsumerWidget {
  const _Attachments({required this.attachments});

  final List<MessageAttachment> attachments;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final token = ref.watch(tokenStoreProvider).accessToken;
    final headers = token == null ? null : {'Authorization': 'Bearer $token'};
    final images = attachments.where((item) => item.kind == AttachmentKind.image);
    final others = attachments.where((item) => item.kind != AttachmentKind.image);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        for (final image in images)
          Padding(
            padding: const EdgeInsets.only(bottom: 4),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(12),
              child: CachedNetworkImage(
                imageUrl: image.url,
                httpHeaders: headers,
                fit: BoxFit.cover,
                width: 240,
                placeholder: (_, _) => Container(
                  width: 240,
                  height: 160,
                  color: AppColors.surfaceMuted,
                ),
                errorWidget: (_, _, _) => Container(
                  width: 240,
                  height: 160,
                  color: AppColors.surfaceMuted,
                  alignment: Alignment.center,
                  child: const Text(
                    'Photo indisponible',
                    style: TextStyle(fontSize: 12, color: AppColors.foregroundMuted),
                  ),
                ),
              ),
            ),
          ),
        for (final other in others)
          Padding(
            padding: const EdgeInsets.all(8),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(
                  other.kind == AttachmentKind.audio
                      ? Icons.mic_none
                      : Icons.videocam_outlined,
                  size: 18,
                ),
                const SizedBox(width: 6),
                Text(
                  other.kind == AttachmentKind.audio
                      ? 'Message vocal (${Fmt.duration(other.duration)})'
                      : 'Video (${Fmt.duration(other.duration)})',
                  style: const TextStyle(fontSize: 13),
                ),
              ],
            ),
          ),
      ],
    );
  }
}

class _EchoBubble extends StatelessWidget {
  const _EchoBubble({required this.text});

  final String text;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(top: 10),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          Container(
            constraints: BoxConstraints(maxWidth: MediaQuery.sizeOf(context).width * 0.74),
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 9),
            decoration: BoxDecoration(
              color: AppColors.brand600.withValues(alpha: 0.7),
              borderRadius: const BorderRadius.only(
                topLeft: Radius.circular(16),
                topRight: Radius.circular(16),
                bottomLeft: Radius.circular(16),
                bottomRight: Radius.circular(6),
              ),
            ),
            child: Text(text, style: const TextStyle(color: Colors.white, height: 1.35)),
          ),
          const Padding(
            padding: EdgeInsets.only(top: 2, right: 4),
            child: Text(
              'Envoi...',
              style: TextStyle(fontSize: 11, color: AppColors.foregroundMuted),
            ),
          ),
        ],
      ),
    );
  }
}

class _Composer extends StatelessWidget {
  const _Composer({
    required this.controller,
    required this.sending,
    required this.onSend,
    required this.onPickImages,
  });

  final TextEditingController controller;
  final bool sending;
  final VoidCallback onSend;
  final VoidCallback onPickImages;

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      top: false,
      child: Container(
        padding: const EdgeInsets.fromLTRB(8, 8, 8, 8),
        decoration: const BoxDecoration(
          color: AppColors.surface,
          border: Border(top: BorderSide(color: AppColors.border)),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            IconButton(
              onPressed: sending ? null : onPickImages,
              icon: const Icon(Icons.add_photo_alternate_outlined),
              tooltip: 'Joindre des photos',
              color: AppColors.foregroundMuted,
            ),
            Expanded(
              child: TextField(
                controller: controller,
                minLines: 1,
                maxLines: 5,
                textCapitalization: TextCapitalization.sentences,
                decoration: const InputDecoration(
                  hintText: 'Écrire un message',
                  isDense: true,
                  contentPadding: EdgeInsets.symmetric(horizontal: 14, vertical: 11),
                ),
              ),
            ),
            const SizedBox(width: 6),
            Material(
              color: sending ? AppColors.brand200 : AppColors.brand600,
              shape: const CircleBorder(),
              child: InkWell(
                customBorder: const CircleBorder(),
                onTap: sending ? null : onSend,
                child: const Padding(
                  padding: EdgeInsets.all(11),
                  child: Icon(Icons.send, size: 20, color: Colors.white),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
