import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/format.dart';
import '../../core/models/rental_request.dart';
import '../../core/network/api_exception.dart';
import '../../core/theme/app_colors.dart';
import '../../shared/widgets/states.dart';
import '../rentals/my_requests_screen.dart';
import '../rentals/rentals_repository.dart';

/// La file des demandes, cote équipe.
///
/// C'est ici que se joue la promesse du schema : vérifier aupres du
/// fournisseur avant de mettre en relation. Le bouton de mise en relation
/// n'apparaît qu'une fois la vérification horodatee, et le serveur
/// refuse de toute facon sans elle.
class ReceivedRequestsScreen extends ConsumerWidget {
  const ReceivedRequestsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final requests = ref.watch(myRequestsProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Demandes reçues')),
      body: requests.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => ErrorView(
          message: '$error'.replaceFirst('ApiException: ', ''),
          onRetry: () => ref.invalidate(myRequestsProvider),
        ),
        data: (page) {
          if (page.results.isEmpty) {
            return const EmptyView(
              icon: Icons.inbox_outlined,
              title: 'Aucune demande',
              description: 'La file est vide.',
            );
          }
          return RefreshIndicator(
            onRefresh: () async {
              ref.invalidate(myRequestsProvider);
              ref.invalidate(pendingSummaryProvider);
            },
            child: ListView.separated(
              padding: const EdgeInsets.all(16),
              itemCount: page.results.length,
              separatorBuilder: (_, _) => const SizedBox(height: 12),
              itemBuilder: (context, index) =>
                  _StaffRequestCard(request: page.results[index]),
            ),
          );
        },
      ),
    );
  }
}

class _StaffRequestCard extends ConsumerStatefulWidget {
  const _StaffRequestCard({required this.request});

  final RentalRequest request;

  @override
  ConsumerState<_StaffRequestCard> createState() => _StaffRequestCardState();
}

class _StaffRequestCardState extends ConsumerState<_StaffRequestCard> {
  bool _busy = false;

  Future<void> _run(Future<RentalRequest> Function() action) async {
    setState(() => _busy = true);
    try {
      await action();
      ref.invalidate(myRequestsProvider);
      ref.invalidate(pendingSummaryProvider);
    } on ApiException catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text(error.message)));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _call(String phone) async {
    final uri = Uri(scheme: 'tel', path: phone);
    if (!await launchUrl(uri) && mounted) {
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text('Appelez le $phone')));
    }
  }

  Future<void> _confirmRelease() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Mettre en relation ?'),
        content: Text(
          'Les coordonnées du fournisseur seront transmises a '
          '${widget.request.clientName ?? 'ce client'}. '
          'Ce geste est date et attribué, et ne se reprend pas.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Annuler'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Mettre en relation'),
          ),
        ],
      ),
    );
    if (confirmed != true) return;
    await _run(
      () => ref.read(rentalsRepositoryProvider).releaseContact(widget.request.id),
    );
  }

  @override
  Widget build(BuildContext context) {
    final request = widget.request;
    final repository = ref.read(rentalsRepositoryProvider);
    final withoutAccount = request.hasAccount == false;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                StatusChip(label: request.statusLabel, tone: _tone(request.status)),
                if (withoutAccount) ...[
                  const SizedBox(width: 6),
                  const StatusChip(label: 'Sans compte', tone: StatusTone.warning),
                ],
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
              request.product?.title ?? 'Bien retiré',
              style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15),
            ),
            const SizedBox(height: 4),
            Text(
              Fmt.rentalPeriodLabel(request.startDate, request.endDate, request.openEnded),
              style: const TextStyle(fontSize: 13, color: AppColors.foregroundMuted),
            ),
            const SizedBox(height: 8),
            _Line(label: 'Demandeur', value: request.clientName ?? 'Inconnu'),
            if (request.supplierName != null)
              _Line(label: 'Fournisseur', value: request.supplierName!),
            if (request.handledByName != null)
              _Line(label: 'Suivi par', value: request.handledByName!),
            if (request.supplierCheckedAt != null)
              _Line(
                label: 'Vérifiée le',
                value: '${Fmt.date(request.supplierCheckedAt!)} '
                    'à ${Fmt.time(request.supplierCheckedAt!)}',
              ),
            if (request.message.isNotEmpty) ...[
              const SizedBox(height: 8),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: AppColors.surfaceMuted,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(request.message, style: const TextStyle(fontSize: 13)),
              ),
            ],

            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                if (request.status == RentalStatus.submitted)
                  OutlinedButton(
                    onPressed: _busy ? null : () => _run(() => repository.markChecking(request.id)),
                    style: _small,
                    child: const Text('Je vérifie'),
                  ),
                if (!request.status.isSettled) ...[
                  OutlinedButton(
                    onPressed:
                        _busy ? null : () => _run(() => repository.markAvailable(request.id)),
                    style: _small,
                    child: const Text('Disponible'),
                  ),
                  OutlinedButton(
                    onPressed: _busy
                        ? null
                        : () => _run(() => repository.markUnavailable(request.id)),
                    style: _small,
                    child: const Text('Indisponible'),
                  ),
                ],
                if (request.canReleaseContact)
                  FilledButton(
                    onPressed: _busy ? null : _confirmRelease,
                    style: FilledButton.styleFrom(
                      minimumSize: const Size(0, 38),
                      padding: const EdgeInsets.symmetric(horizontal: 16),
                    ),
                    child: const Text('Mettre en relation'),
                  ),

                // Un visiteur sans compte n'a pas de fil : le seul moyen
                // de lui répondre est l'appel, et ce numéro est la pour
                // cela. Il ne paraît sur aucune page publique.
                if (withoutAccount && request.requesterPhone != null)
                  OutlinedButton.icon(
                    onPressed: () => _call(request.requesterPhone!),
                    icon: const Icon(Icons.call_outlined, size: 16),
                    label: Text(request.requesterPhone!),
                    style: _small,
                  ),
                if (request.threadId != null)
                  OutlinedButton.icon(
                    onPressed: () => context.push('/messages/${request.threadId}'),
                    icon: const Icon(Icons.forum_outlined, size: 16),
                    label: const Text('Le fil'),
                    style: _small,
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  static final _small = OutlinedButton.styleFrom(
    minimumSize: const Size(0, 38),
    padding: const EdgeInsets.symmetric(horizontal: 14),
    textStyle: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600),
  );

  static StatusTone _tone(RentalStatus status) => switch (status) {
        RentalStatus.submitted => StatusTone.neutral,
        RentalStatus.checking => StatusTone.warning,
        RentalStatus.available => StatusTone.success,
        RentalStatus.connected => StatusTone.brand,
        RentalStatus.unavailable || RentalStatus.cancelled => StatusTone.danger,
      };
}

class _Line extends StatelessWidget {
  const _Line({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(top: 2),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 92,
            child: Text(
              label,
              style: const TextStyle(fontSize: 12, color: AppColors.foregroundMuted),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w500),
            ),
          ),
        ],
      ),
    );
  }
}
