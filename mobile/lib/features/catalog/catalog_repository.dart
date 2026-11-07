import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/models/paginated.dart';
import '../../core/models/product.dart';
import '../../core/network/api_client.dart';
import '../../core/providers.dart';

/// Les criteres d'une recherche dans le catalogue.
class CatalogQuery {
  const CatalogQuery({
    this.search = '',
    this.city = '',
    this.category = '',
    this.ordering = '-created_at',
    this.mine = false,
  });

  final String search;
  final String city;
  final String category;
  final String ordering;

  /// Mes annonces, tous statuts confondus (espace fournisseur).
  final bool mine;

  bool get isFiltered => search.isNotEmpty || city.isNotEmpty || category.isNotEmpty;

  Map<String, dynamic> toParams(int page) {
    return {
      'page': page,
      'ordering': ordering,
      if (search.isNotEmpty) 'search': search,
      if (city.isNotEmpty) 'city': city,
      if (category.isNotEmpty) 'category': category,
      if (mine) 'mine': 'true',
    };
  }

  CatalogQuery copyWith({
    String? search,
    String? city,
    String? category,
    String? ordering,
    bool? mine,
  }) {
    return CatalogQuery(
      search: search ?? this.search,
      city: city ?? this.city,
      category: category ?? this.category,
      ordering: ordering ?? this.ordering,
      mine: mine ?? this.mine,
    );
  }

  @override
  bool operator ==(Object other) =>
      other is CatalogQuery &&
      other.search == search &&
      other.city == city &&
      other.category == category &&
      other.ordering == ordering &&
      other.mine == mine;

  @override
  int get hashCode => Object.hash(search, city, category, ordering, mine);
}

class CatalogRepository {
  CatalogRepository(this._api);

  final ApiClient _api;

  Future<Paginated<Product>> search(CatalogQuery query, {int page = 1}) async {
    final data = await _api.get<Map<String, dynamic>>(
      '/products/',
      query: query.toParams(page),
    );
    return Paginated.fromJson(data, Product.fromJson);
  }

  Future<ProductDetail> detail(String slug) async {
    final data = await _api.get<Map<String, dynamic>>('/products/$slug/');
    return ProductDetail.fromJson(data);
  }

  /// Bascule le favori et renvoie l'état que le serveur a retenu.
  ///
  /// On ne devine pas le nouvel état : deux appuis rapides, ou un autre
  /// appareil, et l'application afficherait un coeur qui ment.
  Future<bool> toggleFavorite(String slug) async {
    final data = await _api.post<Map<String, dynamic>>('/products/$slug/toggle_favorite/');
    return data.boolOf('is_favorite');
  }

  Future<List<String>> favoriteSlugs() async {
    final data = await _api.get<dynamic>('/favorites/slugs/');
    if (data is List) return data.map((item) => '$item').toList();
    if (data is Map && data['slugs'] is List) {
      return (data['slugs'] as List).map((item) => '$item').toList();
    }
    return const [];
  }
}

final catalogRepositoryProvider = Provider<CatalogRepository>((ref) {
  return CatalogRepository(ref.watch(apiClientProvider));
});
