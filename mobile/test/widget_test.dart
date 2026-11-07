import 'package:binogoya/core/format.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:intl/date_symbol_data_local.dart';

void main() {
  setUpAll(() => initializeDateFormatting('fr_FR', null));

  group('Fmt.price', () {
    // Le francais separe les milliers par une espace fine insecable
    // (U+202F), pas par une espace ordinaire. C'est aussi ce que produit
    // `Intl.NumberFormat('fr-FR')` cote site : les deux concordent, et
    // un test ecrit avec une espace normale echouerait pour rien.
    String plain(String value) => value.replaceAll(' ', ' ').replaceAll(' ', ' ');

    test('écrit un montant sans centimes, comme le site', () {
      expect(plain(Fmt.price('25000', 'XOF')), '25 000 XOF');
    });

    test('tolère un prix reçu en chaîne décimale', () {
      // L'API renvoie un DecimalField : « 25000.00 », pas un entier.
      expect(plain(Fmt.price('25000.00', 'XOF')), '25 000 XOF');
    });

    test("arrondit plutôt que d'afficher des centimes de franc CFA", () {
      expect(plain(Fmt.price('1499.60', 'XOF')), '1 500 XOF');
    });
  });

  group('Fmt.dayLabel', () {
    final now = DateTime(2026, 11, 7, 9);

    test("nomme aujourd'hui et hier", () {
      expect(Fmt.dayLabel(DateTime(2026, 11, 7, 23, 30), now), "Aujourd'hui");
      expect(Fmt.dayLabel(DateTime(2026, 11, 6, 0, 5), now), 'Hier');
    });

    test('compte en jours civils, pas en heures', () {
      // Vingt minutes d'ecart, mais la veille : « Hier ».
      expect(
        Fmt.dayLabel(DateTime(2026, 11, 6, 23, 50), DateTime(2026, 11, 7, 0, 10)),
        'Hier',
      );
    });
  });

  group('Fmt.rentalPeriodLabel', () {
    test("dit la durée indéterminée plutôt que d'inventer une fin", () {
      final label = Fmt.rentalPeriodLabel(DateTime(2026, 12, 5), null, true);
      expect(label, contains('indéterminée'));
    });

    test('compte les jours entre deux dates', () {
      final label = Fmt.rentalPeriodLabel(
        DateTime(2026, 12, 5),
        DateTime(2026, 12, 9),
        false,
      );
      expect(label, contains('4 jours'));
    });
  });
}
