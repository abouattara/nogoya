import 'paginated.dart';

/// Le role décide de ce que l'application propose, jamais de ce qu'elle
/// autorise : chaque appel reste revalidé par le serveur. Cacher un
/// bouton n'est pas un controle d'acces.
enum UserRole {
  visitor('visitor'),
  supplier('supplier'),
  admin('admin');

  const UserRole(this.wire);
  final String wire;

  static UserRole parse(String? value) {
    return UserRole.values.firstWhere(
      (role) => role.wire == value,
      orElse: () => UserRole.visitor,
    );
  }
}

/// La personne connectee.
class CurrentUser {
  const CurrentUser({
    required this.id,
    required this.phone,
    required this.firstName,
    required this.lastName,
    required this.email,
    required this.role,
    required this.isStaff,
    required this.avatar,
  });

  final int id;
  final String phone;
  final String firstName;
  final String lastName;
  final String email;
  final UserRole role;
  final bool isStaff;
  final String? avatar;

  bool get isSupplier => role == UserRole.supplier;

  /// Comment nommer la personne a l'ecran, sans jamais retomber sur son
  /// numéro : un numéro affiche comme un nom finit par etre lu par
  /// quelqu'un d'autre.
  String get displayName {
    final full = '$firstName $lastName'.trim();
    return full.isEmpty ? 'Mon compte' : full;
  }

  String get initial {
    final source = displayName.trim();
    return source.isEmpty ? '?' : source[0].toUpperCase();
  }

  factory CurrentUser.fromJson(Map<String, dynamic> json) {
    return CurrentUser(
      id: json.intOf('id'),
      phone: json.str('phone'),
      firstName: json.str('first_name'),
      lastName: json.str('last_name'),
      email: json.str('email'),
      role: UserRole.parse(json.strOrNull('role')),
      isStaff: json.boolOf('is_staff'),
      avatar: json.strOrNull('avatar'),
    );
  }
}

/// Le sous-ensemble public d'un compte, tel qu'il apparaît dans un fil.
class PublicUser {
  const PublicUser({required this.id, required this.fullName, required this.avatar});

  final int id;
  final String fullName;
  final String? avatar;

  String get initial => fullName.trim().isEmpty ? '?' : fullName.trim()[0].toUpperCase();

  factory PublicUser.fromJson(Map<String, dynamic> json) {
    return PublicUser(
      id: json.intOf('id'),
      fullName: json.str('full_name', 'Utilisateur'),
      avatar: json.strOrNull('avatar'),
    );
  }
}
