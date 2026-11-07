import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/theme/app_colors.dart';
import '../auth/session_controller.dart';

/// Ce qu'on voit juste apres avoir envoye une demande.
///
/// L'ecran dit ce qui va se passer et quand, parce que c'est le moment ou
/// l'on se demande si quelque chose est parti. Un visiteur sans compte y
/// lit qu'il sera rappele : il n'a pas de fil ou attendre une réponse, et
/// le laisser guetter une notification qui ne viendra jamais serait la
/// pire fin de parcours possible.
class RequestSentScreen extends ConsumerWidget {
  const RequestSentScreen({super.key, this.threadId});

  final int? threadId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final signedIn = ref.watch(sessionProvider).isSignedIn;

    return Scaffold(
      appBar: AppBar(
        automaticallyImplyLeading: false,
        title: const Text('Demande envoyée'),
      ),
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const SizedBox(height: 24),
            const Icon(Icons.check_circle_outline, size: 64, color: AppColors.brand600),
            const SizedBox(height: 16),
            Text(
              'Votre demande est partie',
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 10),
            Text(
              signedIn
                  ? "L'équipe vérifie la disponibilité auprès du fournisseur, "
                      'puis vous répond dans votre messagerie.'
                  : "L'équipe vérifie la disponibilité auprès du fournisseur, "
                      'puis vous rappelle au numéro que vous avez laissé.',
              textAlign: TextAlign.center,
              style: const TextStyle(height: 1.5, color: AppColors.foregroundMuted),
            ),
            const Spacer(),
            if (signedIn && threadId != null)
              FilledButton.icon(
                onPressed: () => context.go('/messages/$threadId'),
                icon: const Icon(Icons.forum_outlined, size: 20),
                label: const Text('Suivre dans la messagerie'),
              )
            else if (signedIn)
              FilledButton(
                onPressed: () => context.go('/demandes'),
                child: const Text('Voir mes demandes'),
              ),
            const SizedBox(height: 10),
            OutlinedButton(
              onPressed: () => context.go('/'),
              child: const Text('Continuer a chercher'),
            ),
            const SizedBox(height: 8),
          ],
        ),
      ),
    );
  }
}
