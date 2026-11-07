import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/format.dart';
import '../../core/models/product.dart';
import '../../core/theme/app_colors.dart';
import '../../shared/widgets/states.dart';
import 'catalog_controller.dart';

/// La fiche d'un bien.
///
/// Aucun numéro de téléphone n'y figure, meme pour un bien disponible :
/// dans le schema intermediaire, les coordonnées du fournisseur ne
/// circulent qu'apres que l'équipe a vérifie la disponibilité. Le bouton
/// mene donc a une demande, pas a un appel.
class ProductScreen extends ConsumerWidget {
  const ProductScreen({super.key, required this.slug});

  final String slug;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final detail = ref.watch(productDetailProvider(slug));

    return Scaffold(
      appBar: AppBar(title: const Text('Le bien')),
      body: detail.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => ErrorView(
          message: '$error'.replaceFirst('ApiException: ', ''),
          onRetry: () => ref.invalidate(productDetailProvider(slug)),
        ),
        data: (data) => _Body(detail: data),
      ),
      bottomNavigationBar: detail.maybeWhen(
        data: (data) => _RequestBar(detail: data),
        orElse: () => null,
      ),
    );
  }
}

class _Body extends StatelessWidget {
  const _Body({required this.detail});

  final ProductDetail detail;

  @override
  Widget build(BuildContext context) {
    final product = detail.product;

    return ListView(
      padding: EdgeInsets.zero,
      children: [
        _Gallery(images: detail.images, fallback: product.coverImage),
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (product.provenance.isExternal)
                Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child: StatusChip(
                    label: product.sourceName == null
                        ? 'Annonce référencée'
                        : 'Référencée : ${product.sourceName}',
                    tone: StatusTone.neutral,
                  ),
                ),
              Text(product.title, style: Theme.of(context).textTheme.headlineSmall),
              const SizedBox(height: 6),
              Text(
                Fmt.priceWithPeriod(product),
                style: const TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.w700,
                  color: AppColors.brand700,
                ),
              ),
              const SizedBox(height: 12),
              Row(
                children: [
                  const Icon(Icons.place_outlined, size: 16, color: AppColors.foregroundMuted),
                  const SizedBox(width: 4),
                  Expanded(
                    child: Text(
                      detail.placeLine.isEmpty ? 'Lieu non précisé' : detail.placeLine,
                      style: const TextStyle(color: AppColors.foregroundMuted),
                    ),
                  ),
                ],
              ),
              if (detail.categoryName != null) ...[
                const SizedBox(height: 4),
                Row(
                  children: [
                    const Icon(Icons.sell_outlined, size: 16, color: AppColors.foregroundMuted),
                    const SizedBox(width: 4),
                    Text(
                      detail.categoryName!,
                      style: const TextStyle(color: AppColors.foregroundMuted),
                    ),
                  ],
                ),
              ],
              if (detail.description.isNotEmpty) ...[
                const SizedBox(height: 20),
                Text('Description', style: Theme.of(context).textTheme.titleMedium),
                const SizedBox(height: 6),
                Text(detail.description, style: const TextStyle(height: 1.5)),
              ],
              if (detail.attributes.isNotEmpty) ...[
                const SizedBox(height: 20),
                Text('Caractéristiques', style: Theme.of(context).textTheme.titleMedium),
                const SizedBox(height: 8),
                _AttributeTable(attributes: detail.attributes),
              ],
              const SizedBox(height: 24),
              const _HowItWorks(),
            ],
          ),
        ),
      ],
    );
  }
}

/// Le rappel du parcours, pose sous la fiche.
///
/// Sans lui, l'absence de numéro de téléphone passe pour un oubli ou une
/// panne. Dire en trois lignes pourquoi on passe par l'équipe transforme
/// un manque apparent en garantie.
class _HowItWorks extends StatelessWidget {
  const _HowItWorks();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.brand50,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.brand100),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.verified_user_outlined, size: 18, color: AppColors.brand700),
              const SizedBox(width: 6),
              Text(
                'Comment ca se passe',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      color: AppColors.brand800,
                    ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          const Text(
            "Vous envoyez votre demande avec vos dates. L'équipe BINOGOYA "
            "vérifie la disponibilité auprès du fournisseur, puis vous met "
            "en relation. Les coordonnées ne circulent qu'a ce moment.",
            style: TextStyle(height: 1.5, color: AppColors.brand900, fontSize: 13),
          ),
        ],
      ),
    );
  }
}

class _AttributeTable extends StatelessWidget {
  const _AttributeTable({required this.attributes});

  final List<ProductAttributeValue> attributes;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        border: Border.all(color: AppColors.border),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        children: [
          for (var i = 0; i < attributes.length; i++)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
              decoration: BoxDecoration(
                border: i == 0
                    ? null
                    : const Border(top: BorderSide(color: AppColors.border)),
              ),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(
                    flex: 2,
                    child: Text(
                      attributes[i].name,
                      style: const TextStyle(
                        fontSize: 13,
                        color: AppColors.foregroundMuted,
                      ),
                    ),
                  ),
                  Expanded(
                    flex: 3,
                    child: Text(
                      attributes[i].display,
                      style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w500),
                    ),
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }
}

class _Gallery extends StatefulWidget {
  const _Gallery({required this.images, required this.fallback});

  final List<ProductImage> images;
  final String? fallback;

  @override
  State<_Gallery> createState() => _GalleryState();
}

class _GalleryState extends State<_Gallery> {
  final _controller = PageController();
  int _index = 0;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final urls = widget.images.isNotEmpty
        ? widget.images.map((image) => image.url).toList()
        : [if (widget.fallback != null) widget.fallback!];

    if (urls.isEmpty) {
      return Container(
        height: 240,
        color: AppColors.surfaceMuted,
        child: const Icon(Icons.image_outlined, size: 48, color: AppColors.brand300),
      );
    }

    return SizedBox(
      height: 280,
      child: Stack(
        children: [
          PageView.builder(
            controller: _controller,
            itemCount: urls.length,
            onPageChanged: (value) => setState(() => _index = value),
            itemBuilder: (context, index) => CachedNetworkImage(
              imageUrl: urls[index],
              fit: BoxFit.cover,
              width: double.infinity,
              placeholder: (_, _) => Container(color: AppColors.surfaceMuted),
              errorWidget: (_, _, _) => Container(
                color: AppColors.surfaceMuted,
                child: const Icon(Icons.broken_image_outlined, color: AppColors.brand300),
              ),
            ),
          ),
          if (urls.length > 1)
            Positioned(
              bottom: 10,
              left: 0,
              right: 0,
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  for (var i = 0; i < urls.length; i++)
                    Container(
                      width: 7,
                      height: 7,
                      margin: const EdgeInsets.symmetric(horizontal: 3),
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: i == _index
                            ? Colors.white
                            : Colors.white.withValues(alpha: 0.45),
                      ),
                    ),
                ],
              ),
            ),
        ],
      ),
    );
  }
}

class _RequestBar extends StatelessWidget {
  const _RequestBar({required this.detail});

  final ProductDetail detail;

  @override
  Widget build(BuildContext context) {
    final product = detail.product;
    final available =
        product.status == ProductStatus.approved && product.isActive;

    return SafeArea(
      minimum: const EdgeInsets.fromLTRB(16, 8, 16, 12),
      child: FilledButton.icon(
        onPressed: available ? () => context.push('/demander/${product.slug}') : null,
        icon: const Icon(Icons.event_available_outlined, size: 20),
        label: Text(available ? 'Demander ce bien' : "Ce bien n'est plus disponible"),
      ),
    );
  }
}
