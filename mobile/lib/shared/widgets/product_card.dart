import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';

import '../../core/format.dart';
import '../../core/models/product.dart';
import '../../core/theme/app_colors.dart';
import 'states.dart';

/// Une annonce dans une liste.
///
/// Le fournisseur n'est pas nomme ici. Dans le schema intermediaire, le
/// client ne traite jamais avec lui directement, et afficher son nom sur
/// chaque carte invite a le chercher ailleurs, ce que la demande de
/// location existe precisement pour eviter.
class ProductCard extends StatelessWidget {
  const ProductCard({
    super.key,
    required this.product,
    required this.onTap,
    this.onToggleFavorite,
    this.showStatus = false,
    this.trailing,
  });

  final Product product;
  final VoidCallback onTap;
  final VoidCallback? onToggleFavorite;

  /// Vrai dans l'espace fournisseur et la modération, ou l'état compte
  /// autant que le bien lui-meme.
  final bool showStatus;

  final Widget? trailing;

  @override
  Widget build(BuildContext context) {
    return Card(
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: onTap,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            AspectRatio(
              aspectRatio: 4 / 3,
              child: Stack(
                fit: StackFit.expand,
                children: [
                  _Cover(url: product.coverImage),
                  if (onToggleFavorite != null)
                    Positioned(
                      top: 6,
                      right: 6,
                      child: _FavoriteButton(
                        isFavorite: product.isFavorite,
                        onPressed: onToggleFavorite!,
                      ),
                    ),
                  if (showStatus)
                    Positioned(
                      top: 6,
                      left: 6,
                      child: StatusChip(
                        label: product.status.label,
                        tone: _toneFor(product.status),
                      ),
                    ),
                ],
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(10, 8, 10, 10),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    product.title,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      fontWeight: FontWeight.w600,
                      height: 1.25,
                      color: AppColors.foreground,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    product.city.isEmpty ? 'Lieu non précisé' : product.city,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontSize: 12, color: AppColors.foregroundMuted),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    Fmt.priceWithPeriod(product),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      fontWeight: FontWeight.w700,
                      color: AppColors.brand700,
                    ),
                  ),
                  if (trailing != null) ...[const SizedBox(height: 8), trailing!],
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  static StatusTone _toneFor(ProductStatus status) => switch (status) {
        ProductStatus.approved => StatusTone.success,
        ProductStatus.pending || ProductStatus.draft => StatusTone.warning,
        ProductStatus.rejected ||
        ProductStatus.unavailable ||
        ProductStatus.expired =>
          StatusTone.danger,
        ProductStatus.archived => StatusTone.neutral,
      };
}

class _Cover extends StatelessWidget {
  const _Cover({required this.url});

  final String? url;

  @override
  Widget build(BuildContext context) {
    if (url == null || url!.isEmpty) {
      return Container(
        color: AppColors.surfaceMuted,
        child: const Icon(Icons.image_outlined, color: AppColors.brand300, size: 32),
      );
    }
    return CachedNetworkImage(
      imageUrl: url!,
      fit: BoxFit.cover,
      // Le réseau coupe souvent : un placeholder stable vaut mieux qu'un
      // tourniquet qui saute a chaque recyclage de cellule.
      placeholder: (_, _) => Container(color: AppColors.surfaceMuted),
      errorWidget: (_, _, _) => Container(
        color: AppColors.surfaceMuted,
        child: const Icon(Icons.broken_image_outlined, color: AppColors.brand300),
      ),
    );
  }
}

class _FavoriteButton extends StatelessWidget {
  const _FavoriteButton({required this.isFavorite, required this.onPressed});

  final bool isFavorite;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.white.withValues(alpha: 0.92),
      shape: const CircleBorder(),
      child: InkWell(
        customBorder: const CircleBorder(),
        onTap: onPressed,
        child: Padding(
          padding: const EdgeInsets.all(6),
          child: Icon(
            isFavorite ? Icons.favorite : Icons.favorite_border,
            size: 18,
            color: isFavorite ? AppColors.danger600 : AppColors.foregroundMuted,
            semanticLabel: isFavorite ? 'Retirer des favoris' : 'Ajouter aux favoris',
          ),
        ),
      ),
    );
  }
}
