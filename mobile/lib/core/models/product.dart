import 'paginated.dart';

/// Ou en est une annonce dans la file de modération.
enum ProductStatus {
  draft('draft', 'Brouillon'),
  pending('pending', 'En attente'),
  approved('approved', 'Publiée'),
  rejected('rejected', 'Refusée'),
  expired('expired', 'Expirée'),
  unavailable('unavailable', 'Indisponible'),
  archived('archived', 'Archivée');

  const ProductStatus(this.wire, this.label);
  final String wire;
  final String label;

  static ProductStatus parse(String? value) {
    return ProductStatus.values.firstWhere(
      (status) => status.wire == value,
      orElse: () => ProductStatus.pending,
    );
  }
}

/// D'ou vient l'annonce, et donc ce que NOGOYA en garantit.
enum Provenance {
  nogoyaOwner('nogoya_owner'),
  authorizedPartner('authorized_partner'),
  externalReference('external_reference');

  const Provenance(this.wire);
  final String wire;

  bool get isExternal => this != Provenance.nogoyaOwner;

  static Provenance parse(String? value) {
    return Provenance.values.firstWhere(
      (item) => item.wire == value,
      orElse: () => Provenance.nogoyaOwner,
    );
  }
}

/// La période a laquelle se rapporte le prix d'une location.
enum RentalPeriod {
  hour('hour', 'heure'),
  day('day', 'jour'),
  week('week', 'semaine'),
  month('month', 'mois'),
  none('none', '');

  const RentalPeriod(this.wire, this.label);
  final String wire;
  final String label;

  static RentalPeriod parse(String? value) {
    return RentalPeriod.values.firstWhere(
      (item) => item.wire == value,
      orElse: () => RentalPeriod.none,
    );
  }
}

class ProductImage {
  const ProductImage({
    required this.id,
    required this.url,
    required this.isCover,
    required this.order,
    required this.width,
    required this.height,
  });

  final int id;
  final String url;
  final bool isCover;
  final int order;
  final int width;
  final int height;

  factory ProductImage.fromJson(Map<String, dynamic> json) {
    return ProductImage(
      id: json.intOf('id'),
      url: json.str('image'),
      isCover: json.boolOf('is_cover'),
      order: json.intOf('order'),
      width: json.intOf('width'),
      height: json.intOf('height'),
    );
  }
}

/// Une annonce telle qu'elle apparaît dans une liste.
///
/// `supplierName` n'est jamais un numéro de téléphone : le serveur y met
/// le nom public du fournisseur, et retombe sur « Utilisateur » quand il
/// n'y en a pas. C'est un garde-fou serveur, mais l'application ne
/// l'affiche jamais comme un moyen de contact pour autant.
class Product {
  const Product({
    required this.id,
    required this.title,
    required this.slug,
    required this.price,
    required this.currency,
    required this.listingType,
    required this.rentalPeriod,
    required this.city,
    required this.coverImage,
    required this.viewsCount,
    required this.supplierName,
    required this.status,
    required this.isActive,
    required this.isFavorite,
    required this.provenance,
    required this.sourceName,
    required this.categorySlug,
    required this.createdAt,
  });

  final int id;
  final String title;
  final String slug;
  final String price;
  final String currency;
  final String listingType;
  final RentalPeriod rentalPeriod;
  final String city;
  final String? coverImage;
  final int viewsCount;
  final String supplierName;
  final ProductStatus status;
  final bool isActive;
  final bool isFavorite;
  final Provenance provenance;
  final String? sourceName;
  final String? categorySlug;
  final DateTime? createdAt;

  bool get isRental => listingType == 'rent';

  factory Product.fromJson(Map<String, dynamic> json) {
    // `category` est un slug dans une liste, un objet complet dans un
    // detail : la meme cle, deux formes. On ne lit ici que le cas simple.
    final category = json['category'];
    return Product(
      id: json.intOf('id'),
      title: json.str('title'),
      slug: json.str('slug'),
      price: json.str('price', '0'),
      currency: json.str('currency', 'XOF'),
      listingType: json.str('listing_type', 'rent'),
      rentalPeriod: RentalPeriod.parse(json.strOrNull('rental_period')),
      city: json.str('city'),
      coverImage: json.strOrNull('cover_image'),
      viewsCount: json.intOf('views_count'),
      supplierName: json.str('supplier_name', 'Utilisateur'),
      status: ProductStatus.parse(json.strOrNull('status')),
      isActive: json.boolOf('is_active', true),
      isFavorite: json.boolOf('is_favorite'),
      provenance: Provenance.parse(json.strOrNull('provenance')),
      sourceName: json.strOrNull('source_name'),
      categorySlug: category is String ? category : null,
      createdAt: json.dateOf('created_at'),
    );
  }

  Product copyWith({bool? isFavorite}) {
    return Product(
      id: id,
      title: title,
      slug: slug,
      price: price,
      currency: currency,
      listingType: listingType,
      rentalPeriod: rentalPeriod,
      city: city,
      coverImage: coverImage,
      viewsCount: viewsCount,
      supplierName: supplierName,
      status: status,
      isActive: isActive,
      isFavorite: isFavorite ?? this.isFavorite,
      provenance: provenance,
      sourceName: sourceName,
      categorySlug: categorySlug,
      createdAt: createdAt,
    );
  }
}

class ProductAttributeValue {
  const ProductAttributeValue({required this.name, required this.value, required this.unit});

  final String name;
  final String value;
  final String unit;

  /// La valeur telle qu'on la lit, pas telle qu'elle est stockée.
  ///
  /// Un attribut numérique revient du serveur en décimal : une année
  /// s'affichait « 2002.0 » et un kilométrage « 100.0 km ». Le zéro de
  /// queue ne dit rien à personne et fait douter de la fiche, alors on
  /// le retire quand la valeur est entière. « 1.5 m » garde le sien.
  String get display {
    final number = double.tryParse(value);
    final text = (number != null && number == number.roundToDouble())
        ? number.toInt().toString()
        : value;
    return unit.isEmpty ? text : '$text $unit';
  }

  factory ProductAttributeValue.fromJson(Map<String, dynamic> json) {
    return ProductAttributeValue(
      name: json.str('name', json.str('attribute_name')),
      value: json.str('value'),
      unit: json.str('unit'),
    );
  }
}

/// La fiche complete d'une annonce.
class ProductDetail {
  const ProductDetail({
    required this.product,
    required this.description,
    required this.images,
    required this.location,
    required this.region,
    required this.country,
    required this.mapUrl,
    required this.attributes,
    required this.categoryName,
    required this.sourceUrl,
  });

  final Product product;
  final String description;
  final List<ProductImage> images;
  final String location;
  final String region;
  final String country;
  final String? mapUrl;
  final List<ProductAttributeValue> attributes;
  final String? categoryName;

  /// L'annonce d'origine, pour un bien seulement reference par NOGOYA.
  final String sourceUrl;

  /// Les lieux renseignes, du plus precis au plus large, sans doublon.
  String get placeLine {
    final parts = <String>[];
    for (final part in [location, product.city, region, country]) {
      if (part.isNotEmpty && !parts.contains(part)) parts.add(part);
    }
    return parts.join(', ');
  }

  factory ProductDetail.fromJson(Map<String, dynamic> json) {
    final category = json.mapOf('category');
    return ProductDetail(
      product: Product.fromJson(json),
      description: json.str('description'),
      images: json.listOf('images').map(ProductImage.fromJson).toList(),
      location: json.str('location'),
      region: json.str('region'),
      country: json.str('country'),
      mapUrl: json.strOrNull('map_url'),
      attributes: json.listOf('attributes').map(ProductAttributeValue.fromJson).toList(),
      categoryName: category?.strOrNull('name'),
      sourceUrl: json.str('source_url'),
    );
  }
}
