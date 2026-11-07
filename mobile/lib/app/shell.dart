import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../core/theme/app_colors.dart';
import '../features/auth/session_controller.dart';
import '../features/messaging/messaging_repository.dart';

/// La coquille a trois onglets.
///
/// Chaque onglet garde son historique : revenir sur « Chercher » apres
/// un detour par la messagerie retrouve la liste la ou on l'avait
/// laissee, et pas en haut.
class AppShell extends ConsumerWidget {
  const AppShell({super.key, required this.navigationShell});

  /// `StatefulNavigationShell` est déjà l'IndexedStack des branches : il
  /// garde chaque onglet monte, donc son defilement et son historique.
  final StatefulNavigationShell navigationShell;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final signedIn = ref.watch(sessionProvider).isSignedIn;
    // Le compteur ne tourne que pour quelqu'un de connecte : sans
    // session, l'appel partirait toutes les quinze secondes pour un 401.
    final unread = signedIn ? ref.watch(unreadCountProvider).valueOrNull ?? 0 : 0;

    return Scaffold(
      body: navigationShell,
      bottomNavigationBar: NavigationBar(
        selectedIndex: navigationShell.currentIndex,
        onDestinationSelected: (index) => navigationShell.goBranch(
          index,
          // Reappuyer sur l'onglet courant ramene a sa racine : c'est ce
          // que fait tout le monde pour « revenir au debut ».
          initialLocation: index == navigationShell.currentIndex,
        ),
        destinations: [
          const NavigationDestination(
            icon: Icon(Icons.search_outlined),
            selectedIcon: Icon(Icons.search),
            label: 'Chercher',
          ),
          NavigationDestination(
            icon: Badge(
              isLabelVisible: unread > 0,
              label: Text('$unread'),
              backgroundColor: AppColors.accent600,
              child: const Icon(Icons.forum_outlined),
            ),
            selectedIcon: Badge(
              isLabelVisible: unread > 0,
              label: Text('$unread'),
              backgroundColor: AppColors.accent600,
              child: const Icon(Icons.forum),
            ),
            label: 'Messages',
          ),
          const NavigationDestination(
            icon: Icon(Icons.person_outline),
            selectedIcon: Icon(Icons.person),
            label: 'Compte',
          ),
        ],
      ),
    );
  }
}
