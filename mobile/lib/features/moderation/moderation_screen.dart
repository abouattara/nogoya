import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/format.dart';
import '../../core/models/product.dart';
import '../../core/network/api_exception.dart';
import '../../core/theme/app_colors.dart';
import '../../shared/widgets/states.dart';
import '../rentals/rentals_repository.dart';
import 'moderation_repository.dart';

/// L'ecran ou une annonce est acceptee ou refusée.
///
/// Trois partis pris, repris du site :
///
/// * **Toutes les photos, pas la couverture.** On refuse souvent sur la
///   deuxième image.
/// * **Aucune coordonnee du vendeur.** Modérer ne demande pas de savoir
///   qui joindre ; l'ecran serait alors un annuaire.
/// * **Rien n'est masque apres decision.** La carte reste, avec son
///   nouvel état : une erreur de clic doit pouvoir se rattraper.
class ModerationScreen extends ConsumerWidget {
  const ModerationScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final queue = ref.watch(moderationQueueProvider);
    final list = ref.watch(moderationListProvider);
    final pending = ref.watch(pendingSummaryProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Modération'),
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(48),
          child: SizedBox(
            height: 48,
            child: ListView(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 12),
              children: [
                for (final item in ModerationQueue.values)
                  Padding(
                    padding: const EdgeInsets.only(right: 8),
                    child: ChoiceChip(
                      label: Text(item.label),
                      selected: queue == item,
                      onSelected: (_) =>
                          ref.read(moderationQueueProvider.notifier).state = item,
                      selectedColor: AppColors.brand600,
                      labelStyle: TextStyle(
                        fontSize: 13,
                        color: queue == item ? Colors.white : AppColors.foreground,
                        fontWeight: queue == item ? FontWeight.w600 : FontWeight.w400,
                      ),
                    ),
                  ),
              ],
            ),
          ),
        ),
      ),
      body: Column(
        children: [
          pending.maybeWhen(
            data: (summary) => summary.pending == 0
                ? const SizedBox.shrink()
                : _PendingBanner(summary: summary),
            orElse: () => const SizedBox.shrink(),
          ),
          Expanded(
            child: list.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (error, _) => ErrorView(
                message: '$error'.replaceFirst('ApiException: ', ''),
                onRetry: () => ref.invalidate(moderationListProvider),
              ),
              data: (page) {
                if (page.results.isEmpty) {
                  return const EmptyView(
                    icon: Icons.inbox_outlined,
                    title: 'Rien à traiter',
                    description: 'Aucune annonce ne correspond à cette file.',
                  );
                }
                return RefreshIndicator(
                  onRefresh: () async => ref.invalidate(moderationListProvider),
                  child: ListView.separated(
                    padding: const EdgeInsets.all(16),
                    itemCount: page.results.length,
                    separatorBuilder: (_, _) => const SizedBox(height: 14),
                    itemBuilder: (context, index) =>
                        _ModerationCard(detail: page.results[index]),
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

/// Le rappel des demandes en attente, pose la ou l'équipe regarde déjà.
///
/// Une demande venue d'un visiteur sans compte n'a pas de fil : elle
/// n'apparaît dans aucune conversation, et dormirait sans ce compteur,
/// alors que personne ne relancera a la place d'un visiteur anonyme.
class _PendingBanner extends StatelessWidget {
  const _PendingBanner({required this.summary});

  final ({int pending, int withoutAccount}) summary;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: () => context.push('/demandes-recues'),
      child: Container(
        width: double.infinity,
        margin: const EdgeInsets.fromLTRB(16, 12, 16, 0),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: AppColors.brand50,
          border: Border.all(color: AppColors.brand200),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Row(
          children: [
            Expanded(
              child: Text.rich(
                TextSpan(
                  children: [
                    TextSpan(
                      text: '${summary.pending} demande'
                          '${summary.pending > 1 ? 's' : ''} de location',
                      style: const TextStyle(fontWeight: FontWeight.w700),
                    ),
                    TextSpan(
                      text: summary.pending > 1
                          ? ' attendent une vérification'
                          : ' attend une vérification',
                    ),
                    if (summary.withoutAccount > 0)
                      TextSpan(
                        text: ', dont ${summary.withoutAccount} sans compte '
                            'à rappeler par téléphone',
                      ),
                    const TextSpan(text: '.'),
                  ],
                ),
                style: const TextStyle(fontSize: 13, color: AppColors.brand900),
              ),
            ),
            const Icon(Icons.chevron_right, color: AppColors.brand700),
          ],
        ),
      ),
    );
  }
}

class _ModerationCard extends ConsumerStatefulWidget {
  const _ModerationCard({required this.detail});

  final ProductDetail detail;

  @override
  ConsumerState<_ModerationCard> createState() => _ModerationCardState();
}

class _ModerationCardState extends ConsumerState<_ModerationCard> {
  bool _busy = false;

  Future<void> _decide(ModerationDecision decision) async {
    setState(() => _busy = true);
    try {
      await ref
          .read(moderationRepositoryProvider)
          .decide(widget.detail.product.slug, decision);
      ref.invalidate(moderationListProvider);
    } on ApiException catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            error.isForbidden
                ? "Votre compte n'a pas les droits de modération."
                : error.message,
          ),
        ),
      );
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final product = widget.detail.product;
    final images = widget.detail.images;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                StatusChip(label: product.status.label, tone: _tone(product.status)),
                const SizedBox(width: 6),
                if (product.provenance.isExternal)
                  StatusChip(
                    label: product.sourceName ?? 'Source externe',
                    tone: StatusTone.neutral,
                  ),
                const Spacer(),
                if (product.createdAt != null)
                  Text(
                    Fmt.relative(product.createdAt!),
                    style: const TextStyle(
                      fontSize: 11,
                      color: AppColors.foregroundMuted,
                    ),
                  ),
              ],
            ),
            const SizedBox(height: 10),
            Text(
              product.title,
              style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15),
            ),
            const SizedBox(height: 2),
            Text(
              '${widget.detail.placeLine} - ${Fmt.priceWithPeriod(product)}',
              style: const TextStyle(fontSize: 13, color: AppColors.foregroundMuted),
            ),
            Text(
              'Proposée par ${product.supplierName}',
              style: const TextStyle(fontSize: 12, color: AppColors.foregroundMuted),
            ),

            if (widget.detail.description.isNotEmpty) ...[
              const SizedBox(height: 10),
              Text(
                widget.detail.description,
                style: const TextStyle(fontSize: 13, height: 1.4),
              ),
            ],

            const SizedBox(height: 12),
            if (images.isEmpty)
              const Text(
                'Aucune photo : une annonce sans image convertit mal.',
                style: TextStyle(fontSize: 13, color: AppColors.foregroundMuted),
              )
            else
              SizedBox(
                height: 86,
                child: ListView.separated(
                  scrollDirection: Axis.horizontal,
                  itemCount: images.length,
                  separatorBuilder: (_, _) => const SizedBox(width: 8),
                  itemBuilder: (context, index) => ClipRRect(
                    borderRadius: BorderRadius.circular(10),
                    child: CachedNetworkImage(
                      imageUrl: images[index].url,
                      width: 86,
                      height: 86,
                      fit: BoxFit.cover,
                      placeholder: (_, _) => Container(
                        width: 86,
                        height: 86,
                        color: AppColors.surfaceMuted,
                      ),
                      errorWidget: (_, _, _) => Container(
                        width: 86,
                        height: 86,
                        color: AppColors.surfaceMuted,
                        child: const Icon(Icons.broken_image_outlined, size: 18),
                      ),
                    ),
                  ),
                ),
              ),

            const SizedBox(height: 14),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                for (final decision in ModerationDecision.values)
                  if (_isOffered(decision, product.status))
                    decision == ModerationDecision.approve
                        ? FilledButton(
                            onPressed: _busy ? null : () => _decide(decision),
                            style: FilledButton.styleFrom(
                              minimumSize: const Size(0, 38),
                              padding: const EdgeInsets.symmetric(horizontal: 16),
                            ),
                            child: Text(decision.label),
                          )
                        : OutlinedButton(
                            onPressed: _busy ? null : () => _decide(decision),
                            style: OutlinedButton.styleFrom(
                              minimumSize: const Size(0, 38),
                              padding: const EdgeInsets.symmetric(horizontal: 16),
                            ),
                            child: Text(decision.label),
                          ),
                OutlinedButton.icon(
                  onPressed: () => context.push('/produits/${product.slug}'),
                  icon: const Icon(Icons.open_in_new, size: 16),
                  label: const Text('La fiche'),
                  style: OutlinedButton.styleFrom(
                    minimumSize: const Size(0, 38),
                    padding: const EdgeInsets.symmetric(horizontal: 14),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  /// Une decision déjà prise ne se repropose pas.
  static bool _isOffered(ModerationDecision decision, ProductStatus status) {
    return switch (decision) {
      ModerationDecision.approve => status != ProductStatus.approved,
      ModerationDecision.reject => status != ProductStatus.rejected,
      ModerationDecision.unavailable => status != ProductStatus.unavailable,
      ModerationDecision.archive => status != ProductStatus.archived,
    };
  }

  static StatusTone _tone(ProductStatus status) => switch (status) {
        ProductStatus.approved => StatusTone.success,
        ProductStatus.pending || ProductStatus.draft => StatusTone.warning,
        ProductStatus.rejected ||
        ProductStatus.unavailable ||
        ProductStatus.expired =>
          StatusTone.danger,
        ProductStatus.archived => StatusTone.neutral,
      };
}
