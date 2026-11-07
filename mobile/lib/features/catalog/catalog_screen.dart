import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/models/product.dart';
import '../../core/network/api_exception.dart';
import '../../core/theme/app_colors.dart';
import '../../shared/widgets/product_card.dart';
import '../../shared/widgets/states.dart';
import '../auth/session_controller.dart';
import 'catalog_controller.dart';
import 'catalog_repository.dart';

/// L'ecran d'accueil : chercher un bien à louer.
class CatalogScreen extends ConsumerStatefulWidget {
  const CatalogScreen({super.key});

  @override
  ConsumerState<CatalogScreen> createState() => _CatalogScreenState();
}

class _CatalogScreenState extends ConsumerState<CatalogScreen> {
  final _searchController = TextEditingController();
  final _scrollController = ScrollController();
  Timer? _debounce;

  @override
  void initState() {
    super.initState();
    _scrollController.addListener(_onScroll);
  }

  @override
  void dispose() {
    _debounce?.cancel();
    _searchController.dispose();
    _scrollController.removeListener(_onScroll);
    _scrollController.dispose();
    super.dispose();
  }

  void _onScroll() {
    // 600 px avant le bas : sur un réseau lent, attendre d'y etre
    // laisserait un trou blanc au milieu du defilement.
    final position = _scrollController.position;
    if (position.pixels >= position.maxScrollExtent - 600) {
      ref.read(catalogProvider(ref.read(searchQueryProvider)).notifier).loadMore();
    }
  }

  void _onSearchChanged(String value) {
    // On attend que la frappe s'arrete : une requete par lettre saturerait
    // le quota de 120 appels par minute avant la fin du mot.
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 400), () {
      ref.read(searchQueryProvider.notifier).update(
            (query) => query.copyWith(search: value.trim()),
          );
    });
  }

  Future<void> _toggleFavorite(Product product) async {
    if (!ref.read(sessionProvider).isSignedIn) {
      _tell('Connectez-vous pour garder vos favoris.');
      return;
    }
    final query = ref.read(searchQueryProvider);
    final controller = ref.read(catalogProvider(query).notifier);
    // On montre le resultat tout de suite, on corrige si le serveur
    // répond autre chose : un coeur qui met deux secondes a reagir donne
    // l'impression que l'appui n'a pas ete pris.
    controller.markFavorite(product.slug, !product.isFavorite);
    try {
      final actual = await ref
          .read(catalogRepositoryProvider)
          .toggleFavorite(product.slug);
      controller.markFavorite(product.slug, actual);
    } on ApiException catch (error) {
      controller.markFavorite(product.slug, product.isFavorite);
      _tell(error.message);
    }
  }

  void _tell(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context)
      ..clearSnackBars()
      ..showSnackBar(SnackBar(content: Text(message)));
  }

  @override
  Widget build(BuildContext context) {
    final query = ref.watch(searchQueryProvider);
    final state = ref.watch(catalogProvider(query));

    return Scaffold(
      body: RefreshIndicator(
        onRefresh: () => ref.read(catalogProvider(query).notifier).load(),
        child: CustomScrollView(
          controller: _scrollController,
          slivers: [
            SliverAppBar(
              floating: true,
              snap: true,
              titleSpacing: 16,
              title: const Text('BINOGOYA'),
              bottom: PreferredSize(
                preferredSize: const Size.fromHeight(64),
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
                  child: TextField(
                    controller: _searchController,
                    onChanged: _onSearchChanged,
                    textInputAction: TextInputAction.search,
                    decoration: InputDecoration(
                      hintText: 'Que cherchez-vous à louer ?',
                      prefixIcon: const Icon(Icons.search, size: 20),
                      suffixIcon: _searchController.text.isEmpty
                          ? null
                          : IconButton(
                              icon: const Icon(Icons.close, size: 18),
                              tooltip: 'Effacer la recherche',
                              onPressed: () {
                                _searchController.clear();
                                _onSearchChanged('');
                              },
                            ),
                      isDense: true,
                    ),
                  ),
                ),
              ),
            ),
            if (state.loading)
              const SliverToBoxAdapter(child: _LoadingGrid())
            else if (state.error != null && state.items.isEmpty)
              SliverFillRemaining(
                hasScrollBody: false,
                child: ErrorView(
                  message: state.error!,
                  onRetry: () => ref.read(catalogProvider(query).notifier).load(),
                ),
              )
            else if (state.isEmpty)
              SliverFillRemaining(
                hasScrollBody: false,
                child: EmptyView(
                  icon: Icons.search_off,
                  title: 'Aucun bien trouvé',
                  description: query.isFiltered
                      ? 'Essayez avec moins de mots, ou une autre ville.'
                      : "Le catalogue se remplit. Revenez bientôt.",
                ),
              )
            else ...[
              SliverPadding(
                padding: const EdgeInsets.fromLTRB(16, 4, 16, 8),
                sliver: SliverToBoxAdapter(
                  child: Text(
                    '${state.count} bien${state.count > 1 ? 's' : ''} a louer',
                    style: const TextStyle(
                      fontSize: 13,
                      color: AppColors.foregroundMuted,
                    ),
                  ),
                ),
              ),
              SliverPadding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                sliver: SliverGrid(
                  gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
                    // Une colonne sur un petit téléphone, deux des que la
                    // largeur le permet, sans point de rupture ecrit en dur.
                    maxCrossAxisExtent: 240,
                    mainAxisSpacing: 12,
                    crossAxisSpacing: 12,
                    childAspectRatio: 0.72,
                  ),
                  delegate: SliverChildBuilderDelegate(
                    (context, index) {
                      final product = state.items[index];
                      return ProductCard(
                        product: product,
                        onTap: () => context.push('/produits/${product.slug}'),
                        onToggleFavorite: () => _toggleFavorite(product),
                      );
                    },
                    childCount: state.items.length,
                  ),
                ),
              ),
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.symmetric(vertical: 24),
                  child: Center(
                    child: state.loadingMore
                        ? const SizedBox(
                            height: 22,
                            width: 22,
                            child: CircularProgressIndicator(strokeWidth: 2.5),
                          )
                        : state.hasMore
                            ? const SizedBox.shrink()
                            : const Text(
                                'Fin de la liste',
                                style: TextStyle(
                                  fontSize: 12,
                                  color: AppColors.foregroundMuted,
                                ),
                              ),
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _LoadingGrid extends StatelessWidget {
  const _LoadingGrid();

  @override
  Widget build(BuildContext context) {
    return GridView.builder(
      padding: const EdgeInsets.all(16),
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      itemCount: 4,
      gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
        maxCrossAxisExtent: 240,
        mainAxisSpacing: 12,
        crossAxisSpacing: 12,
        childAspectRatio: 0.72,
      ),
      itemBuilder: (context, index) => const Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(child: Shimmer(height: double.infinity, radius: 12)),
          SizedBox(height: 8),
          Shimmer(height: 14, width: 140),
          SizedBox(height: 6),
          Shimmer(height: 12, width: 90),
        ],
      ),
    );
  }
}
