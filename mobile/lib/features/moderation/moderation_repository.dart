import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/models/paginated.dart';
import '../../core/models/product.dart';
import '../../core/network/api_client.dart';
import '../../core/providers.dart';

/// Les files de la modération.
///
/// « À traiter » réunit les annonces des membres et les brouillons issus
/// d'un import : la question posee est la meme, et les separer ferait
/// oublier l'une des deux.
enum ModerationQueue {
  todo('À traiter', ['pending', 'draft']),
  published('Publiées', ['approved']),
  refused('Refusées', ['rejected']),
  withdrawn('Retirées', ['unavailable', 'expired', 'archived']);

  const ModerationQueue(this.label, this.statuses);
  final String label;
  final List<String> statuses;
}

/// Une decision de modération, telle que l'API la nomme.
enum ModerationDecision {
  approve('approve', 'Publier'),
  reject('reject', 'Refuser'),
  unavailable('unavailable', 'Indisponible'),
  archive('archive', 'Archiver');

  const ModerationDecision(this.wire, this.label);
  final String wire;
  final String label;
}

class ModerationRepository {
  ModerationRepository(this._api);

  final ApiClient _api;

  Future<Paginated<ProductDetail>> queue(ModerationQueue queue, {int page = 1}) async {
    final data = await _api.get<Map<String, dynamic>>(
      '/products/moderation/',
      query: {'status': queue.statuses, 'page': page},
    );
    // Le serialiseur de modération porte les photos et la description :
    // on refuse souvent une annonce sur sa deuxième image, pas sur son
    // titre, donc on lit la fiche entiere.
    return Paginated.fromJson(data, ProductDetail.fromJson);
  }

  Future<void> decide(String slug, ModerationDecision decision) async {
    await _api.post<dynamic>(
      '/products/$slug/moderate/',
      data: {'action': decision.wire},
    );
  }
}

final moderationRepositoryProvider = Provider<ModerationRepository>((ref) {
  return ModerationRepository(ref.watch(apiClientProvider));
});

final moderationQueueProvider = StateProvider<ModerationQueue>(
  (ref) => ModerationQueue.todo,
);

final moderationListProvider =
    FutureProvider.autoDispose<Paginated<ProductDetail>>((ref) {
  return ref
      .watch(moderationRepositoryProvider)
      .queue(ref.watch(moderationQueueProvider));
});
