import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/format.dart';
import '../../core/models/paginated.dart';
import '../../core/models/rental_request.dart';
import '../../core/theme/app_colors.dart';
import '../../shared/widgets/states.dart';
import 'rentals_repository.dart';

final myRequestsProvider =
    FutureProvider.autoDispose<Paginated<RentalRequest>>((ref) {
  return ref.watch(rentalsRepositoryProvider).list();
});

/// Mes demandes et leur avancement.
class MyRequestsScreen extends ConsumerWidget {
  const MyRequestsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final requests = ref.watch(myRequestsProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Mes demandes')),
      body: requests.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => ErrorView(
          message: '$error'.replaceFirst('ApiException: ', ''),
          onRetry: () => ref.invalidate(myRequestsProvider),
        ),
        data: (page) {
          if (page.results.isEmpty) {
            return EmptyView(
              icon: Icons.event_note_outlined,
              title: 'Aucune demande',
              description:
                  'Trouvez un bien qui vous convient, puis demandez-le. '
                  "L'équipe vérifie et vous répond.",
              action: FilledButton(
                onPressed: () => context.go('/'),
                child: const Text('Chercher un bien'),
              ),
            );
          }
          return RefreshIndicator(
            onRefresh: () async => ref.invalidate(myRequestsProvider),
            child: ListView.separated(
              padding: const EdgeInsets.all(16),
              itemCount: page.results.length,
              separatorBuilder: (_, _) => const SizedBox(height: 12),
              itemBuilder: (context, index) =>
                  _RequestCard(request: page.results[index]),
            ),
          );
        },
      ),
    );
  }
}

class _RequestCard extends StatelessWidget {
  const _RequestCard({required this.request});

  final RentalRequest request;

  @override
  Widget build(BuildContext context) {
    final product = request.product;

    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: product == null ? null : () => context.push('/produits/${product.slug}'),
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  StatusChip(label: request.statusLabel, tone: _tone(request.status)),
                  const Spacer(),
                  if (request.createdAt != null)
                    Text(
                      Fmt.relative(request.createdAt!),
                      style: const TextStyle(
                        fontSize: 11,
                        color: AppColors.foregroundMuted,
                      ),
                    ),
                ],
              ),
              const SizedBox(height: 10),
              Text(
                product?.title ?? 'Bien retiré',
                style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 15),
              ),
              const SizedBox(height: 4),
              Text(
                Fmt.rentalPeriodLabel(request.startDate, request.endDate, request.openEnded),
                style: const TextStyle(fontSize: 13, color: AppColors.foregroundMuted),
              ),
              if (request.message.isNotEmpty) ...[
                const SizedBox(height: 8),
                Text(
                  request.message,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontSize: 13),
                ),
              ],
              const SizedBox(height: 12),
              _Progress(status: request.status, contactReleased: request.contactReleased),
              if (request.threadId != null) ...[
                const SizedBox(height: 10),
                Align(
                  alignment: Alignment.centerLeft,
                  child: TextButton.icon(
                    onPressed: () => context.push('/messages/${request.threadId}'),
                    icon: const Icon(Icons.forum_outlined, size: 16),
                    label: const Text('Suivre dans la messagerie'),
                    style: TextButton.styleFrom(padding: EdgeInsets.zero),
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }

  static StatusTone _tone(RentalStatus status) => switch (status) {
        RentalStatus.submitted => StatusTone.neutral,
        RentalStatus.checking => StatusTone.warning,
        RentalStatus.available => StatusTone.success,
        RentalStatus.connected => StatusTone.brand,
        RentalStatus.unavailable || RentalStatus.cancelled => StatusTone.danger,
      };
}

/// Les trois temps du parcours, pour savoir ou l'on en est sans lire.
///
/// L'etape « vérifiée » est la seule qui engage NOGOYA : elle ne
/// s'allume que lorsque le fournisseur a répondu, jamais par defaut.
class _Progress extends StatelessWidget {
  const _Progress({required this.status, required this.contactReleased});

  final RentalStatus status;
  final bool contactReleased;

  @override
  Widget build(BuildContext context) {
    final verified = status == RentalStatus.available ||
        status == RentalStatus.unavailable ||
        status == RentalStatus.connected;
    final steps = <(String, bool)>[
      ('Reçue', true),
      ('Vérifiée', verified),
      ('Mise en relation', contactReleased || status == RentalStatus.connected),
    ];

    return Row(
      children: [
        for (var i = 0; i < steps.length; i++) ...[
          if (i > 0)
            Expanded(
              child: Container(
                height: 2,
                margin: const EdgeInsets.symmetric(horizontal: 4),
                color: steps[i].$2 ? AppColors.brand600 : AppColors.border,
              ),
            ),
          Column(
            children: [
              Icon(
                steps[i].$2 ? Icons.check_circle : Icons.radio_button_unchecked,
                size: 16,
                color: steps[i].$2 ? AppColors.brand600 : AppColors.border,
              ),
              const SizedBox(height: 2),
              Text(
                steps[i].$1,
                style: TextStyle(
                  fontSize: 10,
                  color: steps[i].$2 ? AppColors.brand700 : AppColors.foregroundMuted,
                ),
              ),
            ],
          ),
        ],
      ],
    );
  }
}
