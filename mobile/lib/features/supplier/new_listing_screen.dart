import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';

import '../../core/models/product.dart';
import '../../core/network/api_exception.dart';
import '../../core/network/wrapped_multipart.dart';
import '../../core/theme/app_colors.dart';
import '../../shared/widgets/states.dart';
import 'supplier_repository.dart';

/// Publier une annonce depuis le téléphone.
///
/// Un seul ecran qui defile, pas un tunnel en etapes : sur une connexion
/// qui coupe, perdre trois ecrans de saisie parce que la quatrieme n'a
/// pas valide est la facon la plus sure de ne jamais recevoir d'annonce.
class NewListingScreen extends ConsumerStatefulWidget {
  const NewListingScreen({super.key});

  @override
  ConsumerState<NewListingScreen> createState() => _NewListingScreenState();
}

class _NewListingScreenState extends ConsumerState<NewListingScreen> {
  final _formKey = GlobalKey<FormState>();
  final _title = TextEditingController();
  final _description = TextEditingController();
  final _price = TextEditingController();
  final _city = TextEditingController();

  int? _categoryId;
  RentalPeriod _period = RentalPeriod.day;
  final List<XFile> _photos = [];
  bool _busy = false;
  String? _error;
  String? _progress;

  @override
  void dispose() {
    _title.dispose();
    _description.dispose();
    _price.dispose();
    _city.dispose();
    super.dispose();
  }

  Future<void> _addPhotos({required bool fromCamera}) async {
    final picker = ImagePicker();
    // On compresse a la prise : les fichiers bruts de 12 Mpx faisaient
    // echouer l'envoi cote serveur sur le site, et le réseau d'ici ne
    // les supporterait pas davantage.
    const width = 1600.0;
    const quality = 82;

    if (fromCamera) {
      final shot = await picker.pickImage(
        source: ImageSource.camera,
        maxWidth: width,
        maxHeight: width,
        imageQuality: quality,
      );
      if (shot != null) setState(() => _photos.add(shot));
      return;
    }

    final picked = await picker.pickMultiImage(
      maxWidth: width,
      maxHeight: width,
      imageQuality: quality,
      limit: 8 - _photos.length,
    );
    if (picked.isNotEmpty) setState(() => _photos.addAll(picked));
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    if (_categoryId == null) {
      setState(() => _error = 'Choisissez une catégorie.');
      return;
    }
    if (_photos.isEmpty) {
      setState(() => _error = 'Ajoutez au moins une photo : une annonce sans image convertit mal.');
      return;
    }

    setState(() {
      _busy = true;
      _error = null;
      _progress = "Création de l'annonce...";
    });

    final repository = ref.read(supplierRepositoryProvider);
    try {
      final product = await repository.create(
        ListingDraft(
          title: _title.text.trim(),
          categoryId: _categoryId!,
          description: _description.text.trim(),
          price: int.parse(_price.text.trim()),
          rentalPeriod: _period,
          city: _city.text.trim(),
        ),
      );

      final files = <UploadFile>[];
      for (final photo in _photos) {
        files.add(
          UploadFile(
            field: 'images',
            filename: photo.name,
            bytes: await photo.readAsBytes(),
            contentType: photo.mimeType ?? 'image/jpeg',
          ),
        );
      }
      await repository.uploadImages(
        product.slug,
        files,
        onEach: (done, total) {
          if (mounted) setState(() => _progress = 'Envoi des photos $done / $total');
        },
      );

      ref.invalidate(myListingsProvider);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text("Annonce envoyée. L'équipe la lit avant publication."),
        ),
      );
      context.pop();
    } on ApiException catch (error) {
      if (!mounted) return;
      setState(() {
        _busy = false;
        _progress = null;
        _error = error.message;
      });
    } on FormatException {
      if (!mounted) return;
      setState(() {
        _busy = false;
        _progress = null;
        _error = 'Le prix doit être un nombre entier.';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final categories = ref.watch(categoriesProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Publier une annonce')),
      body: Form(
        key: _formKey,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
          children: [
            TextFormField(
              controller: _title,
              textCapitalization: TextCapitalization.sentences,
              decoration: const InputDecoration(
                labelText: 'Titre',
                hintText: 'Tente de reception 10x5m',
              ),
              validator: (value) => (value == null || value.trim().length < 4)
                  ? 'Donnez un titre reconnaissable'
                  : null,
            ),
            const SizedBox(height: 12),

            categories.when(
              loading: () => const Shimmer(height: 56),
              error: (error, _) => ErrorView(
                message: 'Les catégories ne se chargent pas.',
                onRetry: () => ref.invalidate(categoriesProvider),
              ),
              data: (roots) {
                final flat = Category.flatten(roots);
                return DropdownButtonFormField<int>(
                  initialValue: _categoryId,
                  isExpanded: true,
                  decoration: const InputDecoration(labelText: 'Catégorie'),
                  items: [
                    for (final (category, depth) in flat)
                      DropdownMenuItem(
                        value: category.id,
                        // Les branches restent visibles pour se reperer,
                        // mais seules les feuilles se choisissent.
                        enabled: category.children.isEmpty,
                        child: Text(
                          '${'   ' * depth}${category.name}',
                          style: TextStyle(
                            color: category.children.isEmpty
                                ? AppColors.foreground
                                : AppColors.foregroundMuted,
                            fontWeight: category.children.isEmpty
                                ? FontWeight.w400
                                : FontWeight.w600,
                          ),
                        ),
                      ),
                  ],
                  onChanged: (value) => setState(() => _categoryId = value),
                );
              },
            ),
            const SizedBox(height: 12),

            Row(
              children: [
                Expanded(
                  flex: 3,
                  child: TextFormField(
                    controller: _price,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(
                      labelText: 'Prix',
                      suffixText: 'XOF',
                    ),
                    validator: (value) {
                      final parsed = int.tryParse((value ?? '').trim());
                      if (parsed == null || parsed <= 0) return 'Prix invalide';
                      return null;
                    },
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  flex: 2,
                  child: DropdownButtonFormField<RentalPeriod>(
                    initialValue: _period,
                    decoration: const InputDecoration(labelText: 'Par'),
                    items: const [
                      DropdownMenuItem(value: RentalPeriod.hour, child: Text('heure')),
                      DropdownMenuItem(value: RentalPeriod.day, child: Text('jour')),
                      DropdownMenuItem(value: RentalPeriod.week, child: Text('semaine')),
                      DropdownMenuItem(value: RentalPeriod.month, child: Text('mois')),
                    ],
                    onChanged: (value) =>
                        setState(() => _period = value ?? RentalPeriod.day),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),

            TextFormField(
              controller: _city,
              textCapitalization: TextCapitalization.words,
              decoration: const InputDecoration(
                labelText: 'Ville',
                hintText: 'Ouagadougou',
              ),
              validator: (value) =>
                  (value == null || value.trim().isEmpty) ? 'Ville requise' : null,
            ),
            const SizedBox(height: 12),

            TextFormField(
              controller: _description,
              maxLines: 5,
              textCapitalization: TextCapitalization.sentences,
              decoration: const InputDecoration(
                labelText: 'Description',
                hintText: "État, dimensions, ce qui est compris dans le prix...",
                alignLabelWithHint: true,
              ),
              validator: (value) => (value == null || value.trim().length < 20)
                  ? 'Décrivez le bien en quelques phrases'
                  : null,
            ),
            const SizedBox(height: 20),

            Text('Photos', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 4),
            const Text(
              'Des photos recentes, prises par vous. Huit au maximum.',
              style: TextStyle(fontSize: 12, color: AppColors.foregroundMuted),
            ),
            const SizedBox(height: 10),
            _PhotoStrip(
              photos: _photos,
              onRemove: (index) => setState(() => _photos.removeAt(index)),
            ),
            const SizedBox(height: 10),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: _busy || _photos.length >= 8
                        ? null
                        : () => _addPhotos(fromCamera: true),
                    icon: const Icon(Icons.photo_camera_outlined, size: 18),
                    label: const Text('Appareil photo'),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: _busy || _photos.length >= 8
                        ? null
                        : () => _addPhotos(fromCamera: false),
                    icon: const Icon(Icons.photo_library_outlined, size: 18),
                    label: const Text('Galerie'),
                  ),
                ),
              ],
            ),

            if (_error != null) ...[
              const SizedBox(height: 14),
              Text(_error!, style: const TextStyle(color: AppColors.dangerFg)),
            ],
            if (_progress != null) ...[
              const SizedBox(height: 14),
              Row(
                children: [
                  const SizedBox(
                    width: 16,
                    height: 16,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  ),
                  const SizedBox(width: 10),
                  Text(_progress!, style: const TextStyle(fontSize: 13)),
                ],
              ),
            ],

            const SizedBox(height: 20),
            FilledButton(
              onPressed: _busy ? null : _submit,
              child: Text(_busy ? 'Envoi...' : 'Envoyer à la modération'),
            ),
            const SizedBox(height: 10),
            const Text(
              "L'équipe lit chaque annonce avant qu'elle paraisse.",
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 12, color: AppColors.foregroundMuted),
            ),
          ],
        ),
      ),
    );
  }
}

class _PhotoStrip extends StatelessWidget {
  const _PhotoStrip({required this.photos, required this.onRemove});

  final List<XFile> photos;
  final void Function(int index) onRemove;

  @override
  Widget build(BuildContext context) {
    if (photos.isEmpty) {
      return Container(
        height: 90,
        decoration: BoxDecoration(
          color: AppColors.surfaceMuted,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: AppColors.border),
        ),
        alignment: Alignment.center,
        child: const Text(
          'Aucune photo pour le moment',
          style: TextStyle(fontSize: 13, color: AppColors.foregroundMuted),
        ),
      );
    }

    return SizedBox(
      height: 90,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: photos.length,
        separatorBuilder: (_, _) => const SizedBox(width: 8),
        itemBuilder: (context, index) => Stack(
          children: [
            ClipRRect(
              borderRadius: BorderRadius.circular(10),
              child: Image.file(
                File(photos[index].path),
                width: 90,
                height: 90,
                fit: BoxFit.cover,
              ),
            ),
            Positioned(
              top: 2,
              right: 2,
              child: Material(
                color: Colors.black54,
                shape: const CircleBorder(),
                child: InkWell(
                  customBorder: const CircleBorder(),
                  onTap: () => onRemove(index),
                  child: const Padding(
                    padding: EdgeInsets.all(3),
                    child: Icon(Icons.close, size: 14, color: Colors.white),
                  ),
                ),
              ),
            ),
            if (index == 0)
              Positioned(
                bottom: 2,
                left: 2,
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
                  decoration: BoxDecoration(
                    color: Colors.black54,
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: const Text(
                    'Couverture',
                    style: TextStyle(color: Colors.white, fontSize: 9),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}
