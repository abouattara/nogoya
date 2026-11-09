import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { API_URL } from "@/lib/server-api";
import { REFRESH_COOKIE, refreshCookieOptions } from "@/lib/auth-cookies";
import { callUpstream } from "@/lib/upstream";

/**
 * Renouvellement silencieux : lit le cookie httpOnly, l'échange contre un
 * jeton d'accès, et fait tourner le cookie (SIMPLE_JWT
 * ROTATE_REFRESH_TOKENS). Appelé à l'amorçage de l'application et chaque
 * fois qu'un appel porteur reçoit un 401.
 *
 * **Cette route n'efface jamais le cookie, quel que soit le refus.**
 *
 * Elle le faisait, et c'est ce qui déconnectait les gens sans raison
 * apparente. SimpleJWT fait tourner le jeton et met l'ancien sur liste
 * noire à chaque usage : deux appels partis ensemble portent donc le même
 * jeton, l'un gagne et pose le nouveau, l'autre reçoit 401. En effaçant
 * le cookie, le perdant détruisait le jeton tout neuf que le gagnant
 * venait d'écrire — et la session mourait pour de bon.
 *
 * Mesuré en production le 2026-11-09 : trois appels lancés ensemble ont
 * répondu 401, 200, 401, et l'appel suivant 401. Le compte était
 * déconnecté, « Impossible de charger votre profil » à l'écran.
 *
 * Deux onglets ouverts sur le site suffisent à produire cette course : le
 * dédoublonnage du client ne vaut que dans un seul onglet.
 *
 * Ne pas effacer coûte peu : un cookie réellement mort reste là jusqu'à
 * son expiration et chaque renouvellement répond 401, ce que le client
 * traite déjà en affichant l'état déconnecté. Effacer coûte une session
 * valide. L'asymétrie décide. La déconnexion, elle, a sa propre route,
 * qui efface — c'est là que ça se passe.
 */
export async function POST() {
  const store = await cookies();
  const refresh = store.get(REFRESH_COOKIE)?.value;
  if (!refresh) {
    // `code` distingue « aucun cookie » d'un « jeton refusé par l'API ».
    // Le client ne réessaie que le second : sans cookie, il n'y a rien à
    // attendre, et réessayer doublerait les appels de chaque visiteur
    // anonyme.
    return NextResponse.json(
      { detail: "Aucune session.", code: "no_session" },
      { status: 401 },
    );
  }

  const { ok, status, data } = await callUpstream(`${API_URL}/api/v1/auth/refresh/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh }),
  });

  if (!ok) {
    return NextResponse.json(data, { status });
  }

  const { access, refresh: rotated } = data as { access: string; refresh?: string };
  const response = NextResponse.json({ access });
  if (rotated) {
    response.cookies.set(REFRESH_COOKIE, rotated, refreshCookieOptions);
  }
  return response;
}
