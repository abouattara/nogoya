import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/format.dart';
import '../../core/network/api_exception.dart';
import '../../core/theme/app_colors.dart';
import '../../shared/widgets/states.dart';
import '../auth/session_controller.dart';
import '../catalog/catalog_controller.dart';
import 'rentals_repository.dart';

/// Demander un bien.
///
/// Ouvert sans compte, volontairement : exiger une inscription avant la
/// première question fait partir des gens qui seraient revenus. Un
/// visiteur donne alors un nom et un numéro, et l'équipe le rappelle,
/// puisqu'il n'a pas de messagerie ou lui écrire.
class RequestFormScreen extends ConsumerStatefulWidget {
  const RequestFormScreen({super.key, required this.slug});

  final String slug;

  @override
  ConsumerState<RequestFormScreen> createState() => _RequestFormScreenState();
}

class _RequestFormScreenState extends ConsumerState<RequestFormScreen> {
  final _formKey = GlobalKey<FormState>();
  final _message = TextEditingController();
  final _guestName = TextEditingController();
  final _guestPhone = TextEditingController();

  DateTime? _start;
  DateTime? _end;
  bool _openEnded = false;
  bool _sending = false;
  String? _error;

  @override
  void dispose() {
    _message.dispose();
    _guestName.dispose();
    _guestPhone.dispose();
    super.dispose();
  }

  Future<void> _pickDate({required bool isStart}) async {
    final today = DateTime.now();
    final initial = isStart ? (_start ?? today) : (_end ?? _start ?? today);
    final picked = await showDatePicker(
      context: context,
      locale: const Locale('fr'),
      initialDate: initial.isBefore(today) ? today : initial,
      firstDate: today,
      lastDate: today.add(const Duration(days: 730)),
      helpText: isStart ? 'Début de la location' : 'Fin de la location',
      cancelText: 'Annuler',
      confirmText: 'Valider',
    );
    if (picked == null) return;
    setState(() {
      if (isStart) {
        _start = picked;
        // Une fin anterieure au debut n'a pas de sens : on la retiré
        // plutot que de laisser partir une période impossible.
        if (_end != null && _end!.isBefore(picked)) _end = null;
      } else {
        _end = picked;
      }
    });
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    if (_start == null) {
      setState(() => _error = 'Indiquez au moins la date de debut.');
      return;
    }
    if (!_openEnded && _end == null) {
      setState(() => _error = 'Indiquez la date de fin, ou cochez la durée indéterminée.');
      return;
    }

    final detail = ref.read(productDetailProvider(widget.slug)).value;
    if (detail == null) return;

    setState(() {
      _sending = true;
      _error = null;
    });

    try {
      final created = await ref.read(rentalsRepositoryProvider).create(
            RentalDraft(
              productId: detail.product.id,
              startDate: _start,
              endDate: _end,
              openEnded: _openEnded,
              message: _message.text.trim(),
              guestName: _guestName.text.trim(),
              guestPhone: _guestPhone.text.trim(),
            ),
          );
      if (!mounted) return;
      context.pushReplacement('/demande-envoyee', extra: created.threadId);
    } on ApiException catch (error) {
      if (!mounted) return;
      setState(() {
        _sending = false;
        _error = error.message;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final signedIn = ref.watch(sessionProvider).isSignedIn;
    final detail = ref.watch(productDetailProvider(widget.slug));

    return Scaffold(
      appBar: AppBar(title: const Text('Demander ce bien')),
      body: detail.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => ErrorView(
          message: '$error'.replaceFirst('ApiException: ', ''),
          onRetry: () => ref.invalidate(productDetailProvider(widget.slug)),
        ),
        data: (data) => Form(
          key: _formKey,
          child: ListView(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
            children: [
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: AppColors.surfaceMuted,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Row(
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            data.product.title,
                            style: const TextStyle(fontWeight: FontWeight.w600),
                          ),
                          const SizedBox(height: 2),
                          Text(
                            Fmt.priceWithPeriod(data.product),
                            style: const TextStyle(
                              fontSize: 13,
                              color: AppColors.brand700,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 20),

              Text('Vos dates', style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: 8),
              _DateField(
                label: 'Début',
                value: _start,
                onTap: () => _pickDate(isStart: true),
              ),
              const SizedBox(height: 10),
              if (!_openEnded)
                _DateField(
                  label: 'Fin',
                  value: _end,
                  onTap: () => _pickDate(isStart: false),
                ),
              CheckboxListTile(
                value: _openEnded,
                onChanged: (value) => setState(() => _openEnded = value ?? false),
                contentPadding: EdgeInsets.zero,
                controlAffinity: ListTileControlAffinity.leading,
                title: const Text('Je ne sais pas encore quand je rendrai le bien'),
                subtitle: const Text(
                  'Pour une maison ou un local, la date de sortie se décide plus tard.',
                  style: TextStyle(fontSize: 12),
                ),
              ),

              const SizedBox(height: 12),
              TextFormField(
                controller: _message,
                maxLines: 4,
                textCapitalization: TextCapitalization.sentences,
                decoration: const InputDecoration(
                  labelText: 'Votre message',
                  hintText: "Dites ce dont vous avez besoin, l'équipe verifiera.",
                  alignLabelWithHint: true,
                ),
              ),

              if (!signedIn) ...[
                const SizedBox(height: 20),
                Text('Pour vous répondre', style: Theme.of(context).textTheme.titleMedium),
                const SizedBox(height: 4),
                const Text(
                  "Vous n'avez pas de compte : l'équipe vous rappellera à ce "
                  'numéro. Il ne sera jamais affiché sur le site.',
                  style: TextStyle(fontSize: 12, color: AppColors.foregroundMuted),
                ),
                const SizedBox(height: 10),
                TextFormField(
                  controller: _guestName,
                  textCapitalization: TextCapitalization.words,
                  decoration: const InputDecoration(labelText: 'Votre nom'),
                  validator: (value) => (value == null || value.trim().isEmpty)
                      ? 'Indiquez votre nom'
                      : null,
                ),
                const SizedBox(height: 10),
                TextFormField(
                  controller: _guestPhone,
                  keyboardType: TextInputType.phone,
                  decoration: const InputDecoration(
                    labelText: 'Votre téléphone',
                    hintText: '+226 70 00 00 00',
                  ),
                  validator: (value) => (value == null || value.trim().length < 8)
                      ? 'Un numéro est nécessaire pour vous recontacter'
                      : null,
                ),
                const SizedBox(height: 8),
                TextButton(
                  onPressed: () => context.push('/connexion'),
                  child: const Text("J'ai déjà un compte, me connecter"),
                ),
              ],

              if (_error != null) ...[
                const SizedBox(height: 12),
                Text(_error!, style: const TextStyle(color: AppColors.dangerFg)),
              ],

              const SizedBox(height: 20),
              FilledButton(
                onPressed: _sending ? null : _submit,
                child: Text(_sending ? 'Envoi...' : 'Envoyer ma demande'),
              ),
              const SizedBox(height: 12),
              const Text(
                "L'équipe vérifie la disponibilité auprès du fournisseur avant "
                'de vous mettre en relation.',
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 12, color: AppColors.foregroundMuted),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _DateField extends StatelessWidget {
  const _DateField({required this.label, required this.value, required this.onTap});

  final String label;
  final DateTime? value;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(12),
      child: InputDecorator(
        decoration: InputDecoration(
          labelText: label,
          suffixIcon: const Icon(Icons.calendar_today_outlined, size: 18),
        ),
        child: Text(
          value == null ? 'Choisir une date' : Fmt.date(value!),
          style: TextStyle(
            color: value == null ? AppColors.foregroundMuted : AppColors.foreground,
          ),
        ),
      ),
    );
  }
}
