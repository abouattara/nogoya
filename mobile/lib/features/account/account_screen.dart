import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/theme/app_colors.dart';
import '../../shared/widgets/avatar.dart';
import '../../shared/widgets/states.dart';
import '../auth/session_controller.dart';
import '../rentals/rentals_repository.dart';

/// Mon compte, et tout ce qui en depend.
///
/// Les entrees reservees a l'équipe ou aux fournisseurs ne s'affichent
/// que pour eux. C'est du rangement, pas une securite : chaque appel
/// derriere reste revalidé par le serveur, qui refuse un geste que le
/// role n'autorise pas, meme si l'ecran avait ete atteint autrement.
class AccountScreen extends ConsumerWidget {
  const AccountScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final session = ref.watch(sessionProvider);
    final user = session.user;

    if (!session.isSignedIn || user == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('Mon compte')),
        body: EmptyView(
          icon: Icons.person_outline,
          title: 'Pas encore de compte',
          description:
              'Un compte garde vos demandes et vos échanges au même endroit. '
              'Chercher et demander un bien reste possible sans compte.',
          action: Column(
            children: [
              FilledButton(
                onPressed: () => context.push('/connexion'),
                child: const Text('Se connecter'),
              ),
              const SizedBox(height: 8),
              OutlinedButton(
                onPressed: () => context.push('/inscription'),
                child: const Text('Créer un compte'),
              ),
              const SizedBox(height: 16),
              TextButton(
                onPressed: () => context.push('/conditions'),
                child: const Text("Conditions d'utilisation"),
              ),
            ],
          ),
        ),
      );
    }

    final pending = session.canModerate ? ref.watch(pendingSummaryProvider) : null;

    return Scaffold(
      appBar: AppBar(title: const Text('Mon compte')),
      body: ListView(
        children: [
          Padding(
            padding: const EdgeInsets.all(20),
            child: Row(
              children: [
                Avatar(name: user.displayName, url: user.avatar, size: 56),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        user.displayName,
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                      const SizedBox(height: 2),
                      Text(
                        user.isSupplier ? 'Fournisseur' : 'Client',
                        style: const TextStyle(
                          fontSize: 13,
                          color: AppColors.foregroundMuted,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const Divider(),

          _Entry(
            icon: Icons.event_note_outlined,
            label: 'Mes demandes',
            onTap: () => context.push('/demandes'),
          ),

          if (user.isSupplier) ...[
            const _SectionLabel('Espace fournisseur'),
            _Entry(
              icon: Icons.storefront_outlined,
              label: 'Mes annonces',
              onTap: () => context.push('/mes-annonces'),
            ),
            _Entry(
              icon: Icons.add_box_outlined,
              label: 'Publier une annonce',
              onTap: () => context.push('/mes-annonces/nouvelle'),
            ),
          ],

          if (session.canModerate) ...[
            const _SectionLabel('Équipe'),
            _Entry(
              icon: Icons.fact_check_outlined,
              label: 'Modération des annonces',
              onTap: () => context.push('/moderation'),
            ),
            _Entry(
              icon: Icons.inbox_outlined,
              label: 'Demandes reçues',
              badge: pending?.valueOrNull?.pending,
              onTap: () => context.push('/demandes-recues'),
            ),
          ],

          const _SectionLabel('À propos'),
          _Entry(
            icon: Icons.gavel_outlined,
            label: "Conditions d'utilisation",
            onTap: () => context.push('/conditions'),
          ),
          const SizedBox(height: 12),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20),
            child: OutlinedButton.icon(
              onPressed: () => _confirmSignOut(context, ref),
              icon: const Icon(Icons.logout, size: 18),
              label: const Text('Se déconnecter'),
              style: OutlinedButton.styleFrom(foregroundColor: AppColors.dangerFg),
            ),
          ),
          const SizedBox(height: 32),
        ],
      ),
    );
  }

  Future<void> _confirmSignOut(BuildContext context, WidgetRef ref) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Se déconnecter ?'),
        content: const Text(
          'Vos demandes et vos messages restent la. Il faudra vous '
          'reconnecter pour les retrouver.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Annuler'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Se déconnecter'),
          ),
        ],
      ),
    );
    if (confirmed != true) return;
    await ref.read(sessionProvider.notifier).signOut();
  }
}

class _SectionLabel extends StatelessWidget {
  const _SectionLabel(this.label);

  final String label;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 20, 20, 6),
      child: Text(
        label.toUpperCase(),
        style: const TextStyle(
          fontSize: 11,
          fontWeight: FontWeight.w700,
          letterSpacing: 0.6,
          color: AppColors.foregroundMuted,
        ),
      ),
    );
  }
}

class _Entry extends StatelessWidget {
  const _Entry({
    required this.icon,
    required this.label,
    required this.onTap,
    this.badge,
  });

  final IconData icon;
  final String label;
  final VoidCallback onTap;
  final int? badge;

  @override
  Widget build(BuildContext context) {
    return ListTile(
      leading: Icon(icon, color: AppColors.brand700),
      title: Text(label),
      trailing: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (badge != null && badge! > 0)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
              decoration: BoxDecoration(
                color: AppColors.accent500,
                borderRadius: BorderRadius.circular(999),
              ),
              child: Text(
                '$badge',
                style: const TextStyle(
                  color: AppColors.foreground,
                  fontSize: 11,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
          const SizedBox(width: 6),
          const Icon(Icons.chevron_right, color: AppColors.foregroundMuted),
        ],
      ),
      onTap: onTap,
    );
  }
}
