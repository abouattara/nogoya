import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/models/paginated.dart';
import '../../core/models/product.dart';
import '../../core/network/api_client.dart';
import '../../core/network/wrapped_multipart.dart';
import '../../core/providers.dart';

/// Une catégorie du catalogue, avec ses sous-catégories.
class Category {
  const Category({
    required this.id,
    required this.name,
    required this.slug,
    required this.children,
  });

  final int id;
  final String name;
  final String slug;
  final List<Category> children;

  factory Category.fromJson(Map<String, dynamic> json) {
    return Category(
      id: json.intOf('id'),
      name: json.str('name'),
      slug: json.str('slug'),
      children: json.listOf('children').map(Category.fromJson).toList(),
    );
  }

  /// L'arbre mis a plat, pour un simple menu deroulant.
  ///
  /// Une annonce se range dans une feuille : proposer les branches
  /// laisserait publier « Vehicules » sans dire lequel, et la recherche
  /// par sous-catégorie ne retrouverait plus le bien.
  static List<(Category, int)> flatten(List<Category> roots, [int depth = 0]) {
    final result = <(Category, int)>[];
    for (final category in roots) {
      result.add((category, depth));
      result.addAll(flatten(category.children, depth + 1));
    }
    return result;
  }
}

/// Ce qu'une nouvelle annonce contient.
class ListingDraft {
  const ListingDraft({
    required this.title,
    required this.categoryId,
    required this.description,
    required this.price,
    required this.rentalPeriod,
    required this.city,
  });

  final String title;
  final int categoryId;
  final String description;
  final int price;
  final RentalPeriod rentalPeriod;
  final String city;

  Map<String, dynamic> toJson() {
    return {
      'title': title,
      'category': categoryId,
      'description': description,
      'price': price,
      // Le lancement porte sur la location seule. Le serveur refuse de
      // toute facon une vente tant que ce choix tient.
      'listing_type': 'rent',
      'rental_period': rentalPeriod.wire,
      'city': city,
      // Pas de position exacte depuis le téléphone : une annonce de
      // maison publiée avec les coordonnées GPS du salon donne l'adresse
      // de son auteur a tout le monde.
      'location_precision': 'approximate',
    };
  }
}

class SupplierRepository {
  SupplierRepository(this._api);

  final ApiClient _api;

  Future<List<Category>> categories() async {
    final data = await _api.get<dynamic>('/categories/');
    final raw = data is List ? data : (data as Map)['results'] as List? ?? const [];
    return raw
        .whereType<Map>()
        .map((item) => Category.fromJson(Map<String, dynamic>.from(item)))
        .toList();
  }

  Future<Paginated<Product>> myListings({int page = 1}) async {
    final data = await _api.get<Map<String, dynamic>>(
      '/products/',
      query: {'mine': 'true', 'page': page, 'ordering': '-created_at'},
    );
    return Paginated.fromJson(data, Product.fromJson);
  }

  Future<Product> create(ListingDraft draft) async {
    final data = await _api.post<Map<String, dynamic>>('/products/', data: draft.toJson());
    return Product.fromJson(data);
  }

  /// Envoie les photos d'une annonce, une par requete.
  ///
  /// Une par requete, pas six d'un coup : c'est la lecon du site, ou un
  /// envoi groupe faisait echouer tout le lot sur une seule photo trop
  /// lourde, et ou la personne ne savait pas lesquelles etaient passees.
  Future<void> uploadImages(
    String slug,
    List<UploadFile> images, {
    void Function(int done, int total)? onEach,
  }) async {
    for (var index = 0; index < images.length; index++) {
      final payload = encodeMultipart(files: [images[index]]);
      await _api.upload<dynamic>('/products/$slug/upload_images/', payload);
      onEach?.call(index + 1, images.length);
    }
  }

  /// Publie ou depublie une annonce déjà approuvee.
  ///
  /// C'est ainsi qu'un fournisseur retiré un bien qui n'est plus
  /// disponible sans perdre l'annonce ni repasser par la modération.
  Future<bool> toggleActive(String slug) async {
    final data = await _api.post<Map<String, dynamic>>('/products/$slug/toggle_active/');
    return data.boolOf('is_active');
  }
}

final supplierRepositoryProvider = Provider<SupplierRepository>((ref) {
  return SupplierRepository(ref.watch(apiClientProvider));
});

final categoriesProvider = FutureProvider<List<Category>>((ref) {
  return ref.watch(supplierRepositoryProvider).categories();
});

final myListingsProvider = FutureProvider.autoDispose<Paginated<Product>>((ref) {
  return ref.watch(supplierRepositoryProvider).myListings();
});
