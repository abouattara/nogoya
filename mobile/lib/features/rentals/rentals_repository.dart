import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/models/paginated.dart';
import '../../core/models/rental_request.dart';
import '../../core/network/api_client.dart';
import '../../core/providers.dart';

/// Ce qu'une demande de location contient au depart.
class RentalDraft {
  const RentalDraft({
    required this.productId,
    required this.startDate,
    required this.endDate,
    required this.openEnded,
    required this.message,
    this.guestName = '',
    this.guestPhone = '',
  });

  final int productId;
  final DateTime? startDate;
  final DateTime? endDate;

  /// Pour une maison, la date de sortie n'est pas connue a la signature.
  /// Exiger une fin obligeait a en inventer une, et la demande partait
  /// fausse.
  final bool openEnded;

  final String message;

  /// Renseignes seulement par un visiteur sans compte, qui n'a pas de fil
  /// de messagerie : l'équipe le rappelle au téléphone.
  final String guestName;
  final String guestPhone;

  Map<String, dynamic> toJson() {
    return {
      'product': productId,
      if (startDate != null) 'start_date': _isoDate(startDate!),
      if (endDate != null && !openEnded) 'end_date': _isoDate(endDate!),
      'open_ended': openEnded,
      'message': message,
      if (guestName.isNotEmpty) 'guest_name': guestName,
      if (guestPhone.isNotEmpty) 'guest_phone': guestPhone,
    };
  }

  static String _isoDate(DateTime value) {
    final month = value.month.toString().padLeft(2, '0');
    final day = value.day.toString().padLeft(2, '0');
    return '${value.year}-$month-$day';
  }
}

class RentalsRepository {
  RentalsRepository(this._api);

  final ApiClient _api;

  Future<RentalRequest> create(RentalDraft draft) async {
    final data = await _api.post<Map<String, dynamic>>(
      '/rental-requests/',
      data: draft.toJson(),
    );
    return RentalRequest.fromJson(data);
  }

  /// Mes demandes, ou toutes celles de la file pour un compte d'équipe :
  /// le serveur décide du perimetre, pas un parametre que le client
  /// pourrait changer.
  Future<Paginated<RentalRequest>> list({int page = 1}) async {
    final data = await _api.get<Map<String, dynamic>>(
      '/rental-requests/',
      query: {'page': page},
    );
    return Paginated.fromJson(data, RentalRequest.fromJson);
  }

  Future<({int pending, int withoutAccount})> pendingSummary() async {
    final data = await _api.get<Map<String, dynamic>>('/rental-requests/pending-summary/');
    return (
      pending: data.intOf('pending'),
      withoutAccount: data.intOf('without_account'),
    );
  }

  // --- gestes d'équipe ------------------------------------------------

  Future<RentalRequest> markChecking(int id) => _staffAction(id, 'checking');

  Future<RentalRequest> markAvailable(int id) => _staffAction(id, 'available');

  Future<RentalRequest> markUnavailable(int id) => _staffAction(id, 'unavailable');

  /// Transmet les coordonnées du fournisseur au client.
  ///
  /// Le serveur refuse tant que la disponibilité n'a pas ete vérifiée.
  /// L'application cache le bouton dans ce cas, mais c'est le refus du
  /// serveur qui fait foi.
  Future<RentalRequest> releaseContact(int id) => _staffAction(id, 'release-contact');

  Future<RentalRequest> _staffAction(int id, String action) async {
    final data = await _api.post<Map<String, dynamic>>('/rental-requests/$id/$action/');
    return RentalRequest.fromJson(data);
  }
}

final rentalsRepositoryProvider = Provider<RentalsRepository>((ref) {
  return RentalsRepository(ref.watch(apiClientProvider));
});

/// Le compteur de demandes en attente, pour la pastille de l'équipe.
final pendingSummaryProvider =
    FutureProvider.autoDispose<({int pending, int withoutAccount})>((ref) {
  return ref.watch(rentalsRepositoryProvider).pendingSummary();
});
