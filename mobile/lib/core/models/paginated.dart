/// Une page de resultats, telle que DRF la renvoie.
///
/// `{count, next, previous, results}`, vingt elements par page. On garde
/// `next` plutot qu'un numéro de page : c'est le serveur qui décide s'il
/// reste quelque chose, et compter les pages a la main se trompe des que
/// la liste bouge entre deux chargements.
class Paginated<T> {
  const Paginated({
    required this.count,
    required this.results,
    this.next,
    this.previous,
  });

  final int count;
  final List<T> results;
  final String? next;
  final String? previous;

  bool get hasMore => next != null;

  static Paginated<T> fromJson<T>(
    Map<String, dynamic> json,
    T Function(Map<String, dynamic>) itemFromJson,
  ) {
    final raw = (json['results'] as List?) ?? const [];
    return Paginated<T>(
      count: (json['count'] as num?)?.toInt() ?? raw.length,
      next: json['next'] as String?,
      previous: json['previous'] as String?,
      results: raw
          .whereType<Map>()
          .map((item) => itemFromJson(Map<String, dynamic>.from(item)))
          .toList(growable: false),
    );
  }

  Paginated<T> merge(Paginated<T> page) {
    return Paginated<T>(
      count: page.count,
      next: page.next,
      previous: page.previous,
      results: [...results, ...page.results],
    );
  }
}

/// Lectures tolerantes d'un JSON.
///
/// L'API renvoie les montants en chaine (`"25000"`, un `DecimalField`) et
/// laisse parfois un champ absent plutot que nul. Un `as int` direct
/// plantait donc sur des réponses parfaitement valides.
extension JsonReading on Map<String, dynamic> {
  String str(String key, [String fallback = '']) {
    final value = this[key];
    if (value == null) return fallback;
    return '$value';
  }

  String? strOrNull(String key) {
    final value = this[key];
    if (value == null) return null;
    final text = '$value';
    return text.isEmpty ? null : text;
  }

  int intOf(String key, [int fallback = 0]) {
    final value = this[key];
    if (value is num) return value.toInt();
    if (value is String) return int.tryParse(value) ?? fallback;
    return fallback;
  }

  int? intOrNull(String key) {
    final value = this[key];
    if (value is num) return value.toInt();
    if (value is String) return int.tryParse(value);
    return null;
  }

  double doubleOf(String key, [double fallback = 0]) {
    final value = this[key];
    if (value is num) return value.toDouble();
    if (value is String) return double.tryParse(value) ?? fallback;
    return fallback;
  }

  bool boolOf(String key, [bool fallback = false]) {
    final value = this[key];
    if (value is bool) return value;
    if (value is String) return value.toLowerCase() == 'true';
    return fallback;
  }

  DateTime? dateOf(String key) {
    final value = this[key];
    if (value is! String || value.isEmpty) return null;
    return DateTime.tryParse(value)?.toLocal();
  }

  Map<String, dynamic>? mapOf(String key) {
    final value = this[key];
    if (value is Map) return Map<String, dynamic>.from(value);
    return null;
  }

  List<Map<String, dynamic>> listOf(String key) {
    final value = this[key];
    if (value is! List) return const [];
    return value.whereType<Map>().map(Map<String, dynamic>.from).toList();
  }
}
