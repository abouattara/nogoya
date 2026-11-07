import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';

import '../../core/theme/app_colors.dart';

/// La pastille d'identite d'une conversation.
///
/// Une photo quand il y en a une, l'initiale sinon, jamais un rond vide.
/// La teinte est tiree du nom, pas tiree au sort : la meme personne garde
/// la meme couleur d'un ecran a l'autre, ce qui aide a retrouver un fil
/// dans une liste sans lire chaque ligne.
class Avatar extends StatelessWidget {
  const Avatar({super.key, required this.name, this.url, this.size = 44});

  final String name;
  final String? url;
  final double size;

  static const _tones = <(Color, Color)>[
    (AppColors.brand100, AppColors.brand800),
    (AppColors.accent100, AppColors.accent700),
    (Color(0xFFD1FAE5), Color(0xFF065F46)),
    (Color(0xFFFEF3C7), Color(0xFF92400E)),
    (Color(0xFFDBEAFE), Color(0xFF1E40AF)),
  ];

  (Color, Color) get _tone {
    var sum = 0;
    for (final unit in name.codeUnits) {
      sum = (sum + unit) % 9973;
    }
    return _tones[sum % _tones.length];
  }

  @override
  Widget build(BuildContext context) {
    final trimmed = name.trim();
    final initial = trimmed.isEmpty ? '?' : trimmed[0].toUpperCase();
    final (background, foreground) = _tone;

    return ClipOval(
      child: SizedBox(
        width: size,
        height: size,
        child: url != null && url!.isNotEmpty
            ? CachedNetworkImage(
                imageUrl: url!,
                fit: BoxFit.cover,
                placeholder: (_, _) => Container(color: AppColors.surfaceMuted),
                errorWidget: (_, _, _) => _Initial(
                  initial: initial,
                  background: background,
                  foreground: foreground,
                  size: size,
                ),
              )
            : _Initial(
                initial: initial,
                background: background,
                foreground: foreground,
                size: size,
              ),
      ),
    );
  }
}

class _Initial extends StatelessWidget {
  const _Initial({
    required this.initial,
    required this.background,
    required this.foreground,
    required this.size,
  });

  final String initial;
  final Color background;
  final Color foreground;
  final double size;

  @override
  Widget build(BuildContext context) {
    return Container(
      color: background,
      alignment: Alignment.center,
      child: Text(
        initial,
        style: TextStyle(
          color: foreground,
          fontWeight: FontWeight.w700,
          fontSize: size * 0.4,
        ),
      ),
    );
  }
}
