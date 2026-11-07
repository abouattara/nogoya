import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/models/user.dart';
import '../../core/network/api_exception.dart';
import '../../core/theme/app_colors.dart';
import 'auth_repository.dart';
import 'session_controller.dart';

/// Créer un compte.
///
/// La case des conditions part decochee : une case pre-cochee n'est pas
/// un consentement. Elle n'est pas non plus la seule garde : le serveur
/// exige `accept_terms` et inscrit une ligne datee portant la version du
/// texte, de sorte qu'une case recochee depuis un outil ne créé aucun
/// compte.
class RegisterScreen extends ConsumerStatefulWidget {
  const RegisterScreen({super.key});

  @override
  ConsumerState<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends ConsumerState<RegisterScreen> {
  final _formKey = GlobalKey<FormState>();
  final _firstName = TextEditingController();
  final _lastName = TextEditingController();
  final _phone = TextEditingController();
  final _password = TextEditingController();

  UserRole _role = UserRole.visitor;
  bool _acceptTerms = false;
  bool _obscure = true;
  bool _busy = false;
  String? _error;
  Map<String, List<String>> _fieldErrors = const {};

  @override
  void dispose() {
    _firstName.dispose();
    _lastName.dispose();
    _phone.dispose();
    _password.dispose();
    super.dispose();
  }

  String? _serverError(String field) => _fieldErrors[field]?.join(' ');

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    if (!_acceptTerms) {
      setState(() => _error = 'Vous devez accepter les conditions pour créer un compte.');
      return;
    }

    setState(() {
      _busy = true;
      _error = null;
      _fieldErrors = const {};
    });

    try {
      await ref.read(authRepositoryProvider).register(
            phone: _phone.text.trim(),
            firstName: _firstName.text.trim(),
            lastName: _lastName.text.trim(),
            password: _password.text,
            role: _role,
            acceptTerms: _acceptTerms,
          );
      // Le compte existe : on enchaine la connexion plutot que de
      // renvoyer vers un formulaire ou retaper le meme mot de passe.
      await ref.read(sessionProvider.notifier).signIn(
            phone: _phone.text.trim(),
            password: _password.text,
          );
      if (!mounted) return;
      context.go('/');
    } on ApiException catch (error) {
      if (!mounted) return;
      setState(() {
        _busy = false;
        _fieldErrors = error.fieldErrors;
        _error = error.fieldErrors.isEmpty ? error.message : null;
      });
      _formKey.currentState!.validate();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Créer un compte')),
      body: Form(
        key: _formKey,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(20, 24, 20, 32),
          children: [
            SegmentedButton<UserRole>(
              segments: const [
                ButtonSegment(
                  value: UserRole.visitor,
                  label: Text('Je cherche'),
                  icon: Icon(Icons.search, size: 18),
                ),
                ButtonSegment(
                  value: UserRole.supplier,
                  label: Text('Je propose'),
                  icon: Icon(Icons.storefront_outlined, size: 18),
                ),
              ],
              selected: {_role},
              onSelectionChanged: (values) => setState(() => _role = values.first),
            ),
            const SizedBox(height: 20),
            Row(
              children: [
                Expanded(
                  child: TextFormField(
                    controller: _firstName,
                    textCapitalization: TextCapitalization.words,
                    decoration: InputDecoration(
                      labelText: 'Prénom',
                      errorText: _serverError('first_name'),
                    ),
                    validator: (value) =>
                        (value == null || value.trim().isEmpty) ? 'Prénom requis' : null,
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: TextFormField(
                    controller: _lastName,
                    textCapitalization: TextCapitalization.words,
                    decoration: InputDecoration(
                      labelText: 'Nom',
                      errorText: _serverError('last_name'),
                    ),
                    validator: (value) =>
                        (value == null || value.trim().isEmpty) ? 'Nom requis' : null,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _phone,
              keyboardType: TextInputType.phone,
              decoration: InputDecoration(
                labelText: 'Téléphone',
                hintText: '+226 70 00 00 00',
                errorText: _serverError('phone'),
              ),
              validator: (value) =>
                  (value == null || value.trim().length < 8) ? 'Numéro invalide' : null,
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _password,
              obscureText: _obscure,
              decoration: InputDecoration(
                labelText: 'Mot de passe',
                helperText: '8 caractères minimum',
                errorText: _serverError('password'),
                suffixIcon: IconButton(
                  onPressed: () => setState(() => _obscure = !_obscure),
                  tooltip: _obscure ? 'Afficher' : 'Masquer',
                  icon: Icon(
                    _obscure ? Icons.visibility_outlined : Icons.visibility_off_outlined,
                  ),
                ),
              ),
              validator: (value) =>
                  (value == null || value.length < 8) ? '8 caractères minimum' : null,
            ),
            const SizedBox(height: 12),

            CheckboxListTile(
              value: _acceptTerms,
              onChanged: (value) => setState(() => _acceptTerms = value ?? false),
              contentPadding: EdgeInsets.zero,
              controlAffinity: ListTileControlAffinity.leading,
              title: const Text(
                "J'ai lu et j'accepte les conditions et la politique d'utilisation.",
                style: TextStyle(fontSize: 13),
              ),
              subtitle: Padding(
                padding: const EdgeInsets.only(top: 4),
                child: GestureDetector(
                  onTap: () => context.push('/conditions'),
                  child: const Text(
                    'Lire les conditions',
                    style: TextStyle(
                      fontSize: 13,
                      color: AppColors.brand700,
                      decoration: TextDecoration.underline,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ),
            ),
            if (_serverError('accept_terms') != null)
              Text(
                _serverError('accept_terms')!,
                style: const TextStyle(color: AppColors.dangerFg, fontSize: 12),
              ),
            if (_serverError('terms_version') != null)
              Text(
                _serverError('terms_version')!,
                style: const TextStyle(color: AppColors.dangerFg, fontSize: 12),
              ),

            if (_error != null) ...[
              const SizedBox(height: 12),
              Text(_error!, style: const TextStyle(color: AppColors.dangerFg)),
            ],
            const SizedBox(height: 16),
            FilledButton(
              onPressed: _busy ? null : _submit,
              child: Text(_busy ? 'Création...' : 'Créer mon compte'),
            ),
            const SizedBox(height: 12),
            Center(
              child: TextButton(
                onPressed: () => context.pop(),
                child: const Text('Déjà inscrit ? Se connecter'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
