import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../features/account/account_screen.dart';
import '../features/auth/login_screen.dart';
import '../features/auth/register_screen.dart';
import '../features/catalog/catalog_screen.dart';
import '../features/catalog/product_screen.dart';
import '../features/legal/conditions_screen.dart';
import '../features/messaging/conversations_screen.dart';
import '../features/messaging/thread_screen.dart';
import '../features/moderation/moderation_screen.dart';
import '../features/moderation/received_requests_screen.dart';
import '../features/rentals/my_requests_screen.dart';
import '../features/rentals/request_form_screen.dart';
import '../features/rentals/request_sent_screen.dart';
import '../features/supplier/my_listings_screen.dart';
import '../features/supplier/new_listing_screen.dart';
import 'shell.dart';

final _rootKey = GlobalKey<NavigatorState>();
final _shellKey = GlobalKey<NavigatorState>();

/// Les routes de l'application.
///
/// Trois onglets dans une coquille qui ne se demonte pas, et tout le
/// reste empile par-dessus. Aucune route n'est protegee par une
/// redirection : un ecran réservé se montre déjà vide et invite a se
/// connecter, et chaque appel derriere reste revalidé par le serveur.
/// Rediriger en plus ferait clignoter l'application au lancement, le
/// temps que le jeton se relise dans le coffre.
final routerProvider = Provider<GoRouter>((ref) {
  return GoRouter(
    navigatorKey: _rootKey,
    initialLocation: '/',
    routes: [
      StatefulShellRoute.indexedStack(
        builder: (context, state, navigationShell) =>
            AppShell(navigationShell: navigationShell),
        branches: [
          StatefulShellBranch(
            navigatorKey: _shellKey,
            routes: [
              GoRoute(
                path: '/',
                builder: (context, state) => const CatalogScreen(),
              ),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/messages',
                builder: (context, state) => const ConversationsScreen(),
              ),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/compte',
                builder: (context, state) => const AccountScreen(),
              ),
            ],
          ),
        ],
      ),

      GoRoute(
        path: '/produits/:slug',
        parentNavigatorKey: _rootKey,
        builder: (context, state) =>
            ProductScreen(slug: state.pathParameters['slug']!),
      ),
      GoRoute(
        path: '/demander/:slug',
        parentNavigatorKey: _rootKey,
        builder: (context, state) =>
            RequestFormScreen(slug: state.pathParameters['slug']!),
      ),
      GoRoute(
        path: '/demande-envoyee',
        parentNavigatorKey: _rootKey,
        builder: (context, state) => RequestSentScreen(threadId: state.extra as int?),
      ),
      GoRoute(
        path: '/demandes',
        parentNavigatorKey: _rootKey,
        builder: (context, state) => const MyRequestsScreen(),
      ),
      GoRoute(
        path: '/messages/:id',
        parentNavigatorKey: _rootKey,
        builder: (context, state) => ThreadScreen(
          conversationId: int.parse(state.pathParameters['id']!),
        ),
      ),
      GoRoute(
        path: '/mes-annonces',
        parentNavigatorKey: _rootKey,
        builder: (context, state) => const MyListingsScreen(),
        routes: [
          GoRoute(
            path: 'nouvelle',
            parentNavigatorKey: _rootKey,
            builder: (context, state) => const NewListingScreen(),
          ),
        ],
      ),
      GoRoute(
        path: '/moderation',
        parentNavigatorKey: _rootKey,
        builder: (context, state) => const ModerationScreen(),
      ),
      GoRoute(
        path: '/demandes-recues',
        parentNavigatorKey: _rootKey,
        builder: (context, state) => const ReceivedRequestsScreen(),
      ),
      GoRoute(
        path: '/connexion',
        parentNavigatorKey: _rootKey,
        builder: (context, state) => const LoginScreen(),
      ),
      GoRoute(
        path: '/inscription',
        parentNavigatorKey: _rootKey,
        builder: (context, state) => const RegisterScreen(),
      ),
      GoRoute(
        path: '/conditions',
        parentNavigatorKey: _rootKey,
        builder: (context, state) => const ConditionsScreen(),
      ),
    ],
    errorBuilder: (context, state) => Scaffold(
      appBar: AppBar(title: const Text('Page introuvable')),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text("Cette page n'existe pas."),
              const SizedBox(height: 12),
              FilledButton(
                onPressed: () => context.go('/'),
                child: const Text("Revenir à l'accueil"),
              ),
            ],
          ),
        ),
      ),
    ),
  );
});
