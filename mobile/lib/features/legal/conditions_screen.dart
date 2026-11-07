import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/config/app_config.dart';
import '../../core/theme/app_colors.dart';
import '../auth/auth_repository.dart';

/// Les conditions d'utilisation : l'essentiel ici, le texte complet sur le site.
///
/// Recopier les cinq sections en Dart ferait une quatrieme version du
/// meme texte, apres le serveur, le site et la constante de version. Elles
/// divergeraient, et c'est precisement le genre de document ou une
/// divergence se paie. L'application resume ce qui engage la personne,
/// nomme la version qu'elle accepte, et ouvre le texte qui fait foi.
class ConditionsScreen extends StatelessWidget {
  const ConditionsScreen({super.key});

  static const _points = <(IconData, String, String)>[
    (
      Icons.route_outlined,
      'Prise en main',
      "Un fournisseur publie, l'équipe lit l'annonce avant qu'elle "
          'paraisse. Vous demandez un bien avec vos dates. L'
          "équipe vérifie la disponibilité, puis vous met en relation.",
    ),
    (
      Icons.lock_outline,
      'Protection des données',
      'Votre numéro ne paraît sur aucune page publique. Vos echanges ne '
          "sont lisibles que par vous et l'équipe de modération. Rien n'est "
          'vendu a personne.',
    ),
    (
      Icons.gpp_bad_outlined,
      'Arnaque et contenu non sain',
      'Fausse annonce, photo volee, paiement reclame avant vérification, '
          'contenu violent ou haineux : le compte est ferme, et les faits '
          'transmis aux autorites quand ils relevent de la loi.',
    ),
    (
      Icons.balance_outlined,
      'Responsabilite',
      "BINOGOYA met en relation, n'est proprietaire d'aucun bien et n'est "
          'pas partie au contrat. Le fournisseur répond du bien, le client '
          'de son usage et de sa restitution.',
    ),
    (
      Icons.more_horiz,
      'Autres',
      'Dix-huit ans revolus, un compte par personne, vos contenus restent '
          'les votres, droit burkinabe.',
    ),
  ];

  Future<void> _openFullText(BuildContext context) async {
    final url = Uri.parse('${AppConfig.siteBaseUrl}/conditions');
    final opened = await launchUrl(url, mode: LaunchMode.externalApplication);
    if (!opened && context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Ouvrez $url dans votre navigateur.')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Conditions d'utilisation")),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(20, 16, 20, 32),
        children: [
          Text(
            'Version du 5 novembre 2026',
            style: Theme.of(context)
                .textTheme
                .bodySmall
                ?.copyWith(color: AppColors.foregroundMuted),
          ),
          const SizedBox(height: 16),
          const Text(
            'BINOGOYA met en relation des personnes qui possedent un bien a '
            'louer et des personnes qui cherchent a en louer un. Le site ne '
            "loue rien lui-même. Voici ce que vous acceptez en créant un "
            'compte.',
            style: TextStyle(height: 1.5),
          ),
          const SizedBox(height: 20),
          for (final (icon, title, body) in _points) ...[
            _Point(icon: icon, title: title, body: body),
            const SizedBox(height: 14),
          ],
          const SizedBox(height: 8),
          OutlinedButton.icon(
            onPressed: () => _openFullText(context),
            icon: const Icon(Icons.open_in_new, size: 18),
            label: const Text('Lire le texte complet'),
          ),
          const SizedBox(height: 12),
          Text(
            "Le resume ci-dessus n'a pas valeur de contrat. Le texte "
            'complet, dans la version $kTermsVersion, est celui qui '
            "s'applique.",
            style: Theme.of(context)
                .textTheme
                .bodySmall
                ?.copyWith(color: AppColors.foregroundMuted),
          ),
        ],
      ),
    );
  }
}

class _Point extends StatelessWidget {
  const _Point({required this.icon, required this.title, required this.body});

  final IconData icon;
  final String title;
  final String body;

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          padding: const EdgeInsets.all(8),
          decoration: const BoxDecoration(
            color: AppColors.brand50,
            shape: BoxShape.circle,
          ),
          child: Icon(icon, size: 18, color: AppColors.brand700),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(title, style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: 2),
              Text(
                body,
                style: const TextStyle(
                  height: 1.45,
                  fontSize: 13,
                  color: AppColors.foregroundMuted,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}
