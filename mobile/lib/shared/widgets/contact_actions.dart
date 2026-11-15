import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/theme/app_colors.dart';

/// Ouvre le composeur, ou WhatsApp, et dit quoi faire si rien ne s'ouvre.
Future<void> openPhone(BuildContext context, String phone) =>
    _open(context, Uri(scheme: 'tel', path: phone), 'Appelez le $phone');

Future<void> openWhatsApp(BuildContext context, String number) {
  final digits = number.replaceAll(RegExp(r'\D'), '');
  return _open(
    context,
    Uri.parse('https://wa.me/$digits'),
    'Ecrivez au $number sur WhatsApp',
  );
}

Future<void> _open(BuildContext context, Uri uri, String fallback) async {
  final ok = await launchUrl(uri, mode: LaunchMode.externalApplication);
  if (!ok && context.mounted) {
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(fallback)));
  }
}

/// Les boutons Appeler et WhatsApp, cote a cote.
class ContactButtons extends StatelessWidget {
  const ContactButtons({super.key, required this.phone, this.whatsapp = ''});

  final String phone;
  final String whatsapp;

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: [
        if (phone.isNotEmpty)
          FilledButton.icon(
            onPressed: () => openPhone(context, phone),
            icon: const Icon(Icons.call, size: 18),
            label: Text(phone),
            style: FilledButton.styleFrom(
              minimumSize: const Size(0, 40),
              padding: const EdgeInsets.symmetric(horizontal: 14),
            ),
          ),
        if (whatsapp.isNotEmpty)
          OutlinedButton.icon(
            onPressed: () => openWhatsApp(context, whatsapp),
            icon: const Icon(Icons.chat_outlined, size: 18, color: AppColors.successFg),
            label: const Text('WhatsApp'),
            style: OutlinedButton.styleFrom(
              minimumSize: const Size(0, 40),
              padding: const EdgeInsets.symmetric(horizontal: 14),
              foregroundColor: AppColors.successFg,
            ),
          ),
      ],
    );
  }
}
