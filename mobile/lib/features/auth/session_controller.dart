import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/models/user.dart';
import '../../core/providers.dart';
import 'auth_repository.dart';

/// Les trois etats possibles d'une session.
///
/// `loading` est un état a part entiere, pas un « pas encore connecte » :
/// au lancement, on ignore encore s'il reste un jeton dans le coffre, et
/// afficher l'ecran de connexion pendant ce temps ferait clignoter une
/// page que la personne n'a pas demandee.
enum SessionStatus { loading, signedIn, signedOut }

class SessionState {
  const SessionState({required this.status, this.user});

  const SessionState.loading() : this(status: SessionStatus.loading);
  const SessionState.signedOut() : this(status: SessionStatus.signedOut);

  final SessionStatus status;
  final CurrentUser? user;

  bool get isSignedIn => status == SessionStatus.signedIn && user != null;
  bool get isReady => status != SessionStatus.loading;

  /// Le compte peut-il modérer ? Decide de ce que l'application propose,
  /// jamais de ce qu'elle autorise : le serveur revérifie chaque geste.
  bool get canModerate => user?.isStaff ?? false;

  bool get isSupplier => user?.isSupplier ?? false;
}

class SessionController extends StateNotifier<SessionState> {
  SessionController(this._ref) : super(const SessionState.loading()) {
    _restore();
  }

  final Ref _ref;

  AuthRepository get _auth => _ref.read(authRepositoryProvider);

  Future<void> _restore() async {
    final user = await _auth.restore();
    if (!mounted) return;
    state = user == null
        ? const SessionState.signedOut()
        : SessionState(status: SessionStatus.signedIn, user: user);
  }

  Future<void> signIn({required String phone, required String password}) async {
    final user = await _auth.login(phone: phone, password: password);
    if (!mounted) return;
    state = SessionState(status: SessionStatus.signedIn, user: user);
  }

  Future<void> signOut() async {
    await _auth.logout();
    if (!mounted) return;
    state = const SessionState.signedOut();
  }

  /// Appele quand le rafraichissement a echoue pour de bon.
  void forgetSession() {
    if (!mounted) return;
    state = const SessionState.signedOut();
  }

  Future<void> refreshProfile() async {
    if (!state.isSignedIn) return;
    try {
      final user = await _auth.me();
      if (!mounted) return;
      state = SessionState(status: SessionStatus.signedIn, user: user);
    } on Exception {
      // Le profil n'a pas pu etre relu : la session reste valable, et
      // l'ancienne copie suffit a afficher l'ecran.
    }
  }
}

final sessionProvider = StateNotifierProvider<SessionController, SessionState>((ref) {
  final controller = SessionController(ref);
  // Le client HTTP previent ici quand un refresh a definitivement echoue.
  ref.listen<int>(sessionLostProvider, (_, _) => controller.forgetSession());
  return controller;
});
