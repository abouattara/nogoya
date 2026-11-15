import 'package:binogoya/core/models/rental_request.dart';
import 'package:flutter_test/flutter_test.dart';

Map<String, dynamic> demande({Object? contact, Map<String, dynamic> extra = const {}}) => {
      'id': 7,
      'product': null,
      'start_date': '2026-12-01',
      'end_date': '2026-12-04',
      'open_ended': false,
      'message': 'Libre ?',
      'status': contact == null ? 'checking' : 'connected',
      'status_label': 'x',
      'contact_released': contact != null,
      'nights': 4,
      'thread': 19,
      'created_at': '2026-11-14T10:00:00Z',
      'supplier_contact': contact,
      ...extra,
    };

void main() {
  test("pas de coordonnées tant que l'équipe ne les a pas transmises", () {
    // Le serveur envoie `null` jusqu'à la mise en relation : l'écran ne
    // doit rien inventer à partir d'un champ absent.
    final r = RentalRequest.fromJson(demande());
    expect(r.supplierContact, isNull);
    expect(r.supplierPhone, isNull);
  });

  test('les coordonnées transmises sont lues', () {
    final r = RentalRequest.fromJson(demande(contact: {
      'name': 'Issa Ouédraogo',
      'phone': '+22670010001',
      'whatsapp': '+22676010001',
    }));
    expect(r.supplierContact!.name, 'Issa Ouédraogo');
    expect(r.supplierContact!.phone, '+22670010001');
    expect(r.supplierContact!.whatsapp, '+22676010001');
  });

  test("un WhatsApp non autorisé arrive vide, pas absent", () {
    final r = RentalRequest.fromJson(demande(contact: {
      'name': 'Issa',
      'phone': '+22670010001',
      'whatsapp': '',
    }));
    expect(r.supplierContact!.whatsapp, isEmpty);
  });

  test("l'équipe lit le numéro du fournisseur avant la mise en relation", () {
    final r = RentalRequest.fromJson(demande(extra: {
      'supplier_phone': '+22670010001',
      'supplier_whatsapp': '',
    }));
    expect(r.supplierPhone, '+22670010001');
    expect(r.supplierContact, isNull);
  });
}
