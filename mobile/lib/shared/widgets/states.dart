import 'package:flutter/material.dart';

import '../../core/theme/app_colors.dart';

/// Un message d'erreur qui dit quoi faire.
///
/// Toujours avec un bouton : une erreur sans recours laisse la personne
/// devant un ecran mort, et la seule issue devient de tuer l'application.
class ErrorView extends StatelessWidget {
  const ErrorView({super.key, required this.message, this.onRetry});

  final String message;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.cloud_off_outlined, size: 40, color: AppColors.foregroundMuted),
            const SizedBox(height: 12),
            Text(
              message,
              textAlign: TextAlign.center,
              style: const TextStyle(color: AppColors.foregroundMuted),
            ),
            if (onRetry != null) ...[
              const SizedBox(height: 16),
              OutlinedButton.icon(
                onPressed: onRetry,
                icon: const Icon(Icons.refresh, size: 18),
                label: const Text('Réessayer'),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

/// Une liste vide, expliquee.
class EmptyView extends StatelessWidget {
  const EmptyView({
    super.key,
    required this.title,
    required this.description,
    this.icon = Icons.inbox_outlined,
    this.action,
  });

  final String title;
  final String description;
  final IconData icon;
  final Widget? action;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 40, color: AppColors.brand300),
            const SizedBox(height: 12),
            Text(title, style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 6),
            Text(
              description,
              textAlign: TextAlign.center,
              style: const TextStyle(color: AppColors.foregroundMuted),
            ),
            if (action != null) ...[const SizedBox(height: 16), action!],
          ],
        ),
      ),
    );
  }
}

/// Le rectangle gris d'un contenu en cours de chargement.
class Shimmer extends StatelessWidget {
  const Shimmer({super.key, this.height = 16, this.width, this.radius = 8});

  final double height;
  final double? width;
  final double radius;

  @override
  Widget build(BuildContext context) {
    return Container(
      height: height,
      width: width,
      decoration: BoxDecoration(
        color: AppColors.surfaceMuted,
        borderRadius: BorderRadius.circular(radius),
      ),
    );
  }
}

/// Une pastille d'état, lisible sans couleur.
///
/// Le libelle porte le sens a lui seul : un daltonien ou un ecran au
/// soleil ne distinguent pas un fond ambre d'un fond vert.
class StatusChip extends StatelessWidget {
  const StatusChip({super.key, required this.label, required this.tone});

  final String label;
  final StatusTone tone;

  @override
  Widget build(BuildContext context) {
    final (background, foreground) = switch (tone) {
      StatusTone.brand => (AppColors.brand100, AppColors.brand800),
      StatusTone.success => (AppColors.successBg, AppColors.successFg),
      StatusTone.warning => (AppColors.warningBg, AppColors.warningFg),
      StatusTone.danger => (AppColors.dangerBg, AppColors.dangerFg),
      StatusTone.neutral => (AppColors.surfaceMuted, AppColors.foregroundMuted),
    };

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: background,
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        label,
        style: TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: foreground),
      ),
    );
  }
}

enum StatusTone { brand, success, warning, danger, neutral }
