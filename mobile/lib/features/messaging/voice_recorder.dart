import 'dart:async';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:path_provider/path_provider.dart';
import 'package:record/record.dart';

import '../../core/format.dart';
import '../../core/network/wrapped_multipart.dart';
import '../../core/theme/app_colors.dart';

/// Un vocal enregistré, prêt à partir.
class RecordedVoice {
  const RecordedVoice({required this.file, required this.seconds});

  final UploadFile file;
  final int seconds;
}

/// La barre d'enregistrement qui remplace le champ de saisie.
///
/// Elle démarre seule à l'ouverture : on a appuyé sur le micro pour
/// parler, pas pour ouvrir un second écran où appuyer encore. Deux
/// gestes ensuite, et seulement deux : annuler, ou envoyer.
///
/// Le format est de l'AAC dans un conteneur MP4 (`.m4a`) : c'est ce que
/// tout téléphone Android encode en matériel, et ce que le serveur
/// accepte déjà (`audio/mp4`, signature `ftyp`). Le site, lui, envoie du
/// WebM/Opus ; les deux se lisent partout.
class VoiceRecorderBar extends StatefulWidget {
  const VoiceRecorderBar({super.key, required this.onCancel, required this.onSend});

  final VoidCallback onCancel;
  final Future<void> Function(RecordedVoice voice) onSend;

  @override
  State<VoiceRecorderBar> createState() => _VoiceRecorderBarState();
}

class _VoiceRecorderBarState extends State<VoiceRecorderBar> {
  /// La limite du serveur (`MAX_AUDIO_DURATION_SECONDS`). On s'arrête
  /// avant, plutôt que d'enregistrer cinq minutes que le serveur refuse.
  static const _maxSeconds = 300;

  final _recorder = AudioRecorder();
  Timer? _ticker;
  int _seconds = 0;
  bool _recording = false;
  bool _sending = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _start();
  }

  @override
  void dispose() {
    _ticker?.cancel();
    _recorder.dispose();
    super.dispose();
  }

  Future<void> _start() async {
    try {
      if (!await _recorder.hasPermission()) {
        setState(() => _error =
            "Autorisez le micro pour BINOGOYA dans les réglages du téléphone, puis réessayez.");
        return;
      }
      final dir = await getTemporaryDirectory();
      final path = '${dir.path}/vocal-${DateTime.now().millisecondsSinceEpoch}.m4a';
      await _recorder.start(
        const RecordConfig(
          encoder: AudioEncoder.aacLc,
          // 64 kb/s en mono : une voix reste nette, et une minute pèse
          // environ 500 Ko, ce que le réseau d'ici supporte.
          bitRate: 64000,
          sampleRate: 44100,
          numChannels: 1,
        ),
        path: path,
      );
      if (!mounted) return;
      setState(() => _recording = true);
      _ticker = Timer.periodic(const Duration(seconds: 1), (_) {
        if (!mounted) return;
        setState(() => _seconds++);
        if (_seconds >= _maxSeconds) _send();
      });
    } on Exception {
      if (mounted) setState(() => _error = "Le micro n'a pas pu démarrer.");
    }
  }

  Future<void> _cancel() async {
    _ticker?.cancel();
    final path = await _recorder.stop();
    if (path != null) {
      try {
        await File(path).delete();
      } on FileSystemException {
        // Un fichier temporaire oublié sera nettoyé par le système.
      }
    }
    widget.onCancel();
  }

  Future<void> _send() async {
    if (_sending) return;
    _ticker?.cancel();
    setState(() => _sending = true);
    final path = await _recorder.stop();
    if (path == null) {
      widget.onCancel();
      return;
    }
    // Moins d'une seconde, c'est un appui par erreur : on n'envoie pas un
    // vocal vide, que le serveur refuserait de toute façon.
    final seconds = _seconds < 1 ? 1 : _seconds;
    final file = File(path);
    final bytes = await file.readAsBytes();
    if (bytes.length < 1000) {
      widget.onCancel();
      return;
    }
    await widget.onSend(
      RecordedVoice(
        file: UploadFile(
          field: 'audios',
          filename: 'vocal.m4a',
          bytes: bytes,
          contentType: 'audio/mp4',
        ),
        seconds: seconds,
      ),
    );
    try {
      await file.delete();
    } on FileSystemException {
      // Idem : un temporaire.
    }
  }

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
        child: _error != null
            ? Row(
                children: [
                  Expanded(
                    child: Text(_error!, style: const TextStyle(color: AppColors.dangerFg)),
                  ),
                  TextButton(onPressed: widget.onCancel, child: const Text('Fermer')),
                ],
              )
            : Row(
                children: [
                  IconButton(
                    onPressed: _sending ? null : _cancel,
                    icon: const Icon(Icons.delete_outline),
                    tooltip: 'Annuler le vocal',
                    color: AppColors.dangerFg,
                  ),
                  const SizedBox(width: 4),
                  _PulsingDot(active: _recording && !_sending),
                  const SizedBox(width: 10),
                  Text(
                    Fmt.duration(_seconds),
                    style: const TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.w600,
                      fontFeatures: [FontFeature.tabularFigures()],
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      _sending
                          ? 'Envoi…'
                          : _recording
                              ? 'Enregistrement en cours'
                              : 'Préparation du micro…',
                      style: const TextStyle(fontSize: 13, color: AppColors.foregroundMuted),
                    ),
                  ),
                  Material(
                    color: _recording && !_sending ? AppColors.brand600 : AppColors.brand200,
                    shape: const CircleBorder(),
                    child: InkWell(
                      customBorder: const CircleBorder(),
                      onTap: _recording && !_sending ? _send : null,
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

class _PulsingDot extends StatefulWidget {
  const _PulsingDot({required this.active});

  final bool active;

  @override
  State<_PulsingDot> createState() => _PulsingDotState();
}

class _PulsingDotState extends State<_PulsingDot> with SingleTickerProviderStateMixin {
  late final AnimationController _controller = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 900),
  )..repeat(reverse: true);

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return FadeTransition(
      opacity: widget.active
          ? Tween(begin: 0.35, end: 1.0).animate(_controller)
          : const AlwaysStoppedAnimation(0.35),
      child: Container(
        width: 12,
        height: 12,
        decoration: const BoxDecoration(color: AppColors.danger600, shape: BoxShape.circle),
      ),
    );
  }
}
