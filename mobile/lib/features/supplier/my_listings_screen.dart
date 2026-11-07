import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/models/product.dart';
import '../../core/network/api_exception.dart';
import '../../core/theme/app_colors.dart';
import '../../shared/widgets/product_card.dart';
import '../../shared/widgets/states.dart';
import 'supplier_repository.dart';

/// Mes annonces, tous etats confondus.
class MyListingsScreen extends ConsumerWidget {
  const MyListingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final listings = ref.watch(myListingsProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Mes annonces')),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => context.push('/mes-annonces/nouvelle'),
        icon: const Icon(Icons.add),
        label: const Text('Publier'),
        backgroundColor: AppColors.brand600,
        foregroundColor: Colors.white,
      ),
      body: listings.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => ErrorView(
          message: '$error'.replaceFirst('ApiException: ', ''),
          onRetry: () => ref.invalidate(myListingsProvider),
        ),
        data: (page) {
          if (page.results.isEmpty) {
            return const EmptyView(
              icon: Icons.storefront_outlined,
              title: 'Aucune annonce',
              description:
                  'Publiez un bien : il passe par la modération, puis '
                  'apparaît dans le catalogue.',
            );
          }
          return RefreshIndicator(
            onRefresh: () async => ref.invalidate(myListingsProvider),
            child: GridView.builder(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 88),
              itemCount: page.results.length,
              gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
                maxCrossAxisExtent: 240,
                mainAxisSpacing: 12,
                crossAxisSpacing: 12,
                childAspectRatio: 0.62,
              ),
              itemBuilder: (context, index) {
                final product = page.results[index];
                return ProductCard(
                  product: product,
                  showStatus: true,
                  onTap: () => context.push('/produits/${product.slug}'),
                  trailing: _AvailabilityToggle(product: product),
                );
              },
            ),
          );
        },
      ),
    );
  }
}

/// Retirer un bien qui n'est plus disponible, sans perdre l'annonce.
///
/// Seule une annonce approuvee se depublie : avant cela, elle n'est de
/// toute facon visible de personne, et le serveur refuse le geste.
class _AvailabilityToggle extends ConsumerStatefulWidget {
  const _AvailabilityToggle({required this.product});

  final Product product;

  @override
  ConsumerState<_AvailabilityToggle> createState() => _AvailabilityToggleState();
}

class _AvailabilityToggleState extends ConsumerState<_AvailabilityToggle> {
  bool _busy = false;

  Future<void> _toggle() async {
    setState(() => _busy = true);
    try {
      await ref.read(supplierRepositoryProvider).toggleActive(widget.product.slug);
      ref.invalidate(myListingsProvider);
    } on ApiException catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(error.message)));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (widget.product.status != ProductStatus.approved) {
      return Text(
        widget.product.status == ProductStatus.pending
            ? 'En attente de modération'
            : widget.product.status.label,
        style: const TextStyle(fontSize: 11, color: AppColors.foregroundMuted),
      );
    }

    final active = widget.product.isActive;
    return SizedBox(
      width: double.infinity,
      child: OutlinedButton(
        onPressed: _busy ? null : _toggle,
        style: OutlinedButton.styleFrom(
          minimumSize: const Size(0, 34),
          padding: const EdgeInsets.symmetric(horizontal: 8),
          textStyle: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600),
          foregroundColor: active ? AppColors.dangerFg : AppColors.brand700,
        ),
        child: Text(active ? 'Marquer indisponible' : 'Remettre en ligne'),
      ),
    );
  }
}
