import 'package:intl/intl.dart';

import 'models/product.dart';

/// Les mises en forme partagees, calees sur celles du site.
///
/// Les memes regles que `frontend/src/lib/format.ts` : un prix lu sur le
/// téléphone et sur le site doit s'écrire pareil, sinon on doute du prix.
abstract final class Fmt {
  static final _money = NumberFormat.decimalPattern('fr_FR');
  static final _time = DateFormat('HH:mm', 'fr_FR');
  static final _dayLong = DateFormat('d MMMM y', 'fr_FR');
  static final _dayShort = DateFormat('d MMMM', 'fr_FR');
  static final _weekday = DateFormat('EEEE d MMMM', 'fr_FR');

  /// « 25 000 XOF ». Pas de decimales : aucun loyer ne s'exprime au centime.
  static String price(String raw, String currency) {
    final value = double.tryParse(raw) ?? 0;
    return '${_money.format(value.round())} $currency';
  }

  /// « 25 000 XOF / jour » pour une location, le prix seul pour une vente.
  static String priceWithPeriod(Product product) {
    final base = price(product.price, product.currency);
    if (!product.isRental || product.rentalPeriod == RentalPeriod.none) return base;
    return '$base / ${product.rentalPeriod.label}';
  }

  static String time(DateTime value) => _time.format(value);

  static String date(DateTime value) => _dayLong.format(value);

  /// « Aujourd'hui », « Hier », « lundi 3 novembre », puis la date longue.
  ///
  /// La comparaison porte sur la date civile, pas sur un ecart en heures :
  /// a 00 h 10, un message de 23 h 50 est d'hier, meme s'il a vingt
  /// minutes.
  static String dayLabel(DateTime value, [DateTime? now]) {
    final today = now ?? DateTime.now();
    DateTime midnight(DateTime d) => DateTime(d.year, d.month, d.day);
    final days = midnight(today).difference(midnight(value)).inDays;

    if (days == 0) return "Aujourd'hui";
    if (days == 1) return 'Hier';
    if (days < 7 && days > 0) return _weekday.format(value);
    return value.year == today.year ? _dayShort.format(value) : _dayLong.format(value);
  }

  /// « à l'instant », « il y a 5 min », « il y a 2 h », puis la date.
  static String relative(DateTime value, [DateTime? now]) {
    final seconds = (now ?? DateTime.now()).difference(value).inSeconds;
    if (seconds < 60) return "à l'instant";
    if (seconds < 3600) return 'il y a ${seconds ~/ 60} min';
    if (seconds < 86400) return 'il y a ${seconds ~/ 3600} h';
    if (seconds < 7 * 86400) return 'il y a ${seconds ~/ 86400} j';
    return _dayShort.format(value);
  }

  /// La période d'une demande, telle qu'on la relit dans un recapitulatif.
  static String rentalPeriodLabel(DateTime? start, DateTime? end, bool openEnded) {
    final from = start == null ? null : _dayShort.format(start);
    if (openEnded) {
      return from == null ? 'Durée indéterminée' : 'À partir du $from, durée indéterminée';
    }
    if (from == null || end == null) return 'Dates à préciser';
    final nights = end.difference(start!).inDays;
    final count = nights <= 1 ? '1 jour' : '$nights jours';
    return 'Du $from au ${_dayShort.format(end)} ($count)';
  }

  /// 78 -> « 1:18 », pour la durée d'un message vocal.
  static String duration(int totalSeconds) {
    final safe = totalSeconds < 0 ? 0 : totalSeconds;
    final minutes = safe ~/ 60;
    final seconds = (safe % 60).toString().padLeft(2, '0');
    return '$minutes:$seconds';
  }
}
