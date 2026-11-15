import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:just_audio/just_audio.dart';
import 'package:path_provider/path_provider.dart';

import '../../core/format.dart';
import '../../core/models/message.dart';
import '../../core/theme/app_colors.dart';
import 'messaging_repository.dart';

/// Un message vocal dans une bulle.
///
/// Le fichier n'est téléchargé qu'au premier appui sur lecture. Un fil
/// peut contenir des dizaines de vocaux ; les tirer tous à l'ouverture
/// viderait le forfait de quelqu'un qui voulait seulement lire le
/// dernier message.
///
/// Le téléchargement passe par le client HTTP de l'application, avec le
/// jeton : l'API ne sert ces fichiers qu'aux participants du fil, et un
/// lecteur qui ouvrirait l'URL lui-même partirait sans autorisation.
/// Le fichier est ensuite gardé dans le cache du téléphone, pour qu'une
/// seconde écoute ne le retélécharge pas.
class VoicePlayer extends ConsumerStatefulWidget {
  const VoicePlayer({super.key, required this.attachment, required this.mine});

  final MessageAttachment attachment;

  /// Dans une bulle à moi, sur fond bleu : le lecteur passe en blanc.
  final bool mine;

  @override
  ConsumerState<VoicePlayer> createState() => _VoicePlayerState();
}

class _VoicePlayerState extends ConsumerState<VoicePlayer> {
  AudioPlayer? _player;
  bool _loading = false;
  String? _error;

  @override
  void dispose() {
    _player?.dispose();
    super.dispose();
  }

  Future<File> _localFile() async {
    final dir = await getTemporaryDirectory();
    return File('${dir.path}/vocal-${widget.attachment.id}.audio');
  }

  Future<void> _toggle() async {
    final player = _player;
    if (player != null) {
      if (player.playing) {
        await player.pause();
      } else {
        // Revenu à la fin : on repart du début plutôt que de rester muet.
        if (player.processingState == ProcessingState.completed) {
          await player.seek(Duration.zero);
        }
        await player.play();
      }
      return;
    }

    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final file = await _localFile();
      if (!await file.exists() || await file.length() == 0) {
        final bytes = await ref
            .read(messagingRepositoryProvider)
            .downloadAttachment(widget.attachment.url);
        await file.writeAsBytes(bytes, flush: true);
      }
      final created = AudioPlayer();
      await created.setFilePath(file.path);
      if (!mounted) {
        await created.dispose();
        return;
      }
      setState(() {
        _player = created;
        _loading = false;
      });
      await created.play();
    } on Exception {
      if (mounted) {
        setState(() {
          _loading = false;
          _error = 'Vocal indisponible';
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final foreground = widget.mine ? Colors.white : AppColors.brand700;
    final track = widget.mine ? Colors.white.withValues(alpha: 0.35) : AppColors.brand100;
    final total = Duration(seconds: widget.attachment.duration);
    final player = _player;

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 4),
      child: SizedBox(
        width: 220,
        child: Row(
          children: [
            SizedBox(
              width: 40,
              height: 40,
              child: _loading
                  ? Padding(
                      padding: const EdgeInsets.all(10),
                      child: CircularProgressIndicator(strokeWidth: 2.5, color: foreground),
                    )
                  : StreamBuilder<PlayerState>(
                      stream: player?.playerStateStream,
                      builder: (context, snapshot) {
                        final playing = snapshot.data?.playing ?? false;
                        final ended =
                            snapshot.data?.processingState == ProcessingState.completed;
                        return IconButton(
                          padding: EdgeInsets.zero,
                          onPressed: _toggle,
                          tooltip: playing && !ended ? 'Mettre en pause' : 'Écouter le vocal',
                          icon: Icon(
                            playing && !ended
                                ? Icons.pause_circle_filled
                                : Icons.play_circle_filled,
                            size: 36,
                            color: foreground,
                          ),
                        );
                      },
                    ),
            ),
            const SizedBox(width: 6),
            Expanded(
              child: _error != null
                  ? Text(_error!, style: TextStyle(fontSize: 12, color: foreground))
                  : StreamBuilder<Duration>(
                      stream: player?.positionStream,
                      builder: (context, snapshot) {
                        final position = snapshot.data ?? Duration.zero;
                        final length = player?.duration ?? total;
                        final ratio = length.inMilliseconds == 0
                            ? 0.0
                            : (position.inMilliseconds / length.inMilliseconds).clamp(0.0, 1.0);
                        final shown = player == null ? length : length - position;
                        return Column(
                          mainAxisSize: MainAxisSize.min,
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            ClipRRect(
                              borderRadius: BorderRadius.circular(4),
                              child: LinearProgressIndicator(
                                value: ratio,
                                minHeight: 4,
                                backgroundColor: track,
                                color: foreground,
                              ),
                            ),
                            const SizedBox(height: 4),
                            Text(
                              Fmt.duration(shown.inSeconds),
                              style: TextStyle(fontSize: 11, color: foreground),
                            ),
                          ],
                        );
                      },
                    ),
            ),
          ],
        ),
      ),
    );
  }
}
