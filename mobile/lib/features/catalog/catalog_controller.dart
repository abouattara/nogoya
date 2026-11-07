import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/models/product.dart';
import '../../core/network/api_exception.dart';
import 'catalog_repository.dart';

/// L'état d'une liste d'annonces qui se charge page par page.
class CatalogState {
  const CatalogState({
    this.items = const [],
    this.loading = true,
    this.loadingMore = false,
    this.error,
    this.count = 0,
    this.nextPage,
  });

  final List<Product> items;
  final bool loading;
  final bool loadingMore;
  final String? error;
  final int count;

  /// Null quand le serveur dit qu'il n'y a plus rien.
  final int? nextPage;

  bool get hasMore => nextPage != null;
  bool get isEmpty => !loading && error == null && items.isEmpty;

  CatalogState copyWith({
    List<Product>? items,
    bool? loading,
    bool? loadingMore,
    Object? error = _keep,
    int? count,
    Object? nextPage = _keep,
  }) {
    return CatalogState(
      items: items ?? this.items,
      loading: loading ?? this.loading,
      loadingMore: loadingMore ?? this.loadingMore,
      error: error == _keep ? this.error : error as String?,
      count: count ?? this.count,
      nextPage: nextPage == _keep ? this.nextPage : nextPage as int?,
    );
  }

  static const _keep = Object();
}

/// Charge une recherche, et la suite quand on arrive en bas.
class CatalogController extends StateNotifier<CatalogState> {
  CatalogController(this._repository, this._query) : super(const CatalogState()) {
    load();
  }

  final CatalogRepository _repository;
  final CatalogQuery _query;

  Future<void> load() async {
    state = state.copyWith(loading: true, error: null);
    try {
      final page = await _repository.search(_query);
      state = CatalogState(
        items: page.results,
        loading: false,
        count: page.count,
        nextPage: page.hasMore ? 2 : null,
      );
    } on ApiException catch (error) {
      state = state.copyWith(loading: false, error: error.message);
    }
  }

  Future<void> loadMore() async {
    final next = state.nextPage;
    // Deux appels concurrents colleraient la meme page deux fois : le
    // defilement declenche volontiers plusieurs fois de suite.
    if (next == null || state.loadingMore || state.loading) return;

    state = state.copyWith(loadingMore: true);
    try {
      final page = await _repository.search(_query, page: next);
      state = state.copyWith(
        items: [...state.items, ...page.results],
        loadingMore: false,
        count: page.count,
        nextPage: page.hasMore ? next + 1 : null,
      );
    } on ApiException catch (error) {
      // La page suivante a echoue : on garde ce qui est déjà affiche,
      // vider la liste pour une erreur de pagination serait absurde.
      state = state.copyWith(loadingMore: false, error: error.message);
    }
  }

  /// Reflete localement un favori bascule depuis une fiche.
  void markFavorite(String slug, bool isFavorite) {
    state = state.copyWith(
      items: [
        for (final item in state.items)
          item.slug == slug ? item.copyWith(isFavorite: isFavorite) : item,
      ],
    );
  }
}

/// Une liste par jeu de criteres, detruite des que plus personne ne l'ecoute.
final catalogProvider =
    StateNotifierProvider.family<CatalogController, CatalogState, CatalogQuery>(
  (ref, query) => CatalogController(ref.watch(catalogRepositoryProvider), query),
);

/// Les criteres de l'ecran de recherche.
final searchQueryProvider = StateProvider<CatalogQuery>((ref) => const CatalogQuery());

final productDetailProvider =
    FutureProvider.family.autoDispose<ProductDetail, String>((ref, slug) {
  return ref.watch(catalogRepositoryProvider).detail(slug);
});
