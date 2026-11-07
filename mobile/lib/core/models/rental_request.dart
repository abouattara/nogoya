import 'paginated.dart';
import 'product.dart';

/// Ou en est une demande de location.
///
/// L'ordre des valeurs suit le parcours reel : reçue, vérifiée aupres du
/// fournisseur, puis disponible ou non, puis mise en relation. C'est cet
/// ordre que l'ecran affiche, et c'est pourquoi `connected` ne peut pas
/// venir avant une vérification.
enum RentalStatus {
  submitted('submitted', 'Reçue'),
  checking('checking', 'Vérification en cours'),
  available('available', 'Disponible'),
  unavailable('unavailable', 'Indisponible'),
  connected('connected', 'Mise en relation faite'),
  cancelled('cancelled', 'Annulée');

  const RentalStatus(this.wire, this.label);
  final String wire;
  final String label;

  bool get isSettled =>
      this == RentalStatus.connected ||
      this == RentalStatus.unavailable ||
      this == RentalStatus.cancelled;

  static RentalStatus parse(String? value) {
    return RentalStatus.values.firstWhere(
      (status) => status.wire == value,
      orElse: () => RentalStatus.submitted,
    );
  }
}

/// Une demande de location, cote client comme cote équipe.
///
/// Les champs d'équipe (`requesterPhone`, `clientName`, `staffNote`...)
/// n'arrivent que pour un compte habilite : le serialiseur du client ne
/// les envoie pas du tout. Ils sont donc nullables ici, et l'ecran client
/// ne les lit jamais.
class RentalRequest {
  const RentalRequest({
    required this.id,
    required this.product,
    required this.startDate,
    required this.endDate,
    required this.openEnded,
    required this.message,
    required this.status,
    required this.statusLabel,
    required this.contactReleased,
    required this.nights,
    required this.threadId,
    required this.createdAt,
    this.clientName,
    this.supplierName,
    this.handledByName,
    this.requesterPhone,
    this.hasAccount,
    this.supplierCheckedAt,
    this.contactReleasedAt,
    this.staffNote,
  });

  final int id;
  final Product? product;
  final DateTime? startDate;
  final DateTime? endDate;

  /// « Je ne sais pas encore quand je rendrai le bien ».
  ///
  /// Indispensable pour une maison : exiger une date de fin forcait a en
  /// inventer une, et la demande partait fausse.
  final bool openEnded;

  final String message;
  final RentalStatus status;
  final String statusLabel;
  final bool contactReleased;
  final int nights;

  /// Le fil ou suivre la demande. Absent pour un visiteur sans compte,
  /// qui n'a pas de messagerie : l'équipe le rappelle au téléphone.
  final int? threadId;

  final DateTime? createdAt;

  final String? clientName;
  final String? supplierName;
  final String? handledByName;
  final String? requesterPhone;
  final bool? hasAccount;
  final DateTime? supplierCheckedAt;
  final DateTime? contactReleasedAt;
  final String? staffNote;

  /// Mettre en relation sur un bien non vérifie est la seule faute que ce
  /// schema existe pour eviter : le serveur le refuse, et l'application
  /// n'affiche donc pas le bouton.
  bool get canReleaseContact => supplierCheckedAt != null && !contactReleased;

  factory RentalRequest.fromJson(Map<String, dynamic> json) {
    final product = json.mapOf('product');
    return RentalRequest(
      id: json.intOf('id'),
      product: product == null ? null : Product.fromJson(product),
      startDate: json.dateOf('start_date'),
      endDate: json.dateOf('end_date'),
      openEnded: json.boolOf('open_ended'),
      message: json.str('message'),
      status: RentalStatus.parse(json.strOrNull('status')),
      statusLabel: json.str('status_label'),
      contactReleased: json.boolOf('contact_released'),
      nights: json.intOf('nights'),
      threadId: json.intOrNull('thread'),
      createdAt: json.dateOf('created_at'),
      clientName: json.strOrNull('client_name'),
      supplierName: json.strOrNull('supplier_name'),
      handledByName: json.strOrNull('handled_by_name'),
      requesterPhone: json.strOrNull('requester_phone'),
      hasAccount: json.containsKey('has_account') ? json.boolOf('has_account') : null,
      supplierCheckedAt: json.dateOf('supplier_checked_at'),
      contactReleasedAt: json.dateOf('contact_released_at'),
      staffNote: json.strOrNull('staff_note'),
    );
  }
}
