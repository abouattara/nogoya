import { beforeEach, describe, expect, it, vi } from "vitest";

import { POST } from "./route";
import { REFRESH_COOKIE } from "@/lib/auth-cookies";

const { cookieStore, callUpstream } = vi.hoisted(() => ({
  cookieStore: { value: undefined as string | undefined },
  callUpstream: vi.fn(),
}));

vi.mock("next/headers", () => ({
  cookies: async () => ({
    get: (name: string) =>
      name === "nogoya_refresh" && cookieStore.value !== undefined
        ? { value: cookieStore.value }
        : undefined,
  }),
}));

vi.mock("@/lib/upstream", () => ({ callUpstream }));
vi.mock("@/lib/server-api", () => ({ API_URL: "http://api.test" }));

/** Ce que la réponse demande au navigateur de faire du cookie. */
function cookieInstruction(response: Response) {
  const header = response.headers.get("set-cookie") ?? "";
  if (!header.includes(REFRESH_COOKIE)) return "rien";
  // Un effacement se reconnaît à son expiration dans le passé ou à son
  // Max-Age nul.
  return /Max-Age=0|Expires=Thu, 01 Jan 1970/i.test(header) ? "efface" : "pose";
}

describe("POST /api/auth/refresh", () => {
  beforeEach(() => {
    cookieStore.value = "jeton-valide";
    callUpstream.mockReset();
  });

  it("pose le jeton renouvelé quand l'API accepte", async () => {
    callUpstream.mockResolvedValue({
      ok: true,
      status: 200,
      data: { access: "acces-neuf", refresh: "refresh-neuf" },
    });

    const response = await POST();

    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({ access: "acces-neuf" });
    expect(cookieInstruction(response)).toBe("pose");
  });

  it("n'efface JAMAIS le cookie sur un refus de l'API", async () => {
    // Le défaut qui déconnectait les gens : SimpleJWT fait tourner le
    // jeton et met l'ancien sur liste noire. Deux appels partis ensemble
    // portent le même jeton ; le perdant reçoit 401. S'il efface le
    // cookie, il détruit le jeton tout neuf que le gagnant vient de
    // poser, et la session meurt pour de bon.
    //
    // Mesuré en production : 401, 200, 401 en parallèle, puis 401 à
    // l'appel suivant.
    for (const status of [400, 401, 403, 500]) {
      callUpstream.mockResolvedValue({
        ok: false,
        status,
        data: { detail: "refusé" },
      });

      const response = await POST();

      expect(response.status, `statut ${status}`).toBe(status);
      expect(cookieInstruction(response), `statut ${status}`).toBe("rien");
    }
  });

  it("répond sans appeler l'API quand il n'y a aucun cookie", async () => {
    cookieStore.value = undefined;

    const response = await POST();

    expect(response.status).toBe(401);
    expect(callUpstream).not.toHaveBeenCalled();
    // Le marqueur dit au client de ne pas réessayer : sans cookie, il
    // n'y a rien à attendre, et chaque visiteur anonyme paierait un
    // second appel pour rien.
    expect((await response.json()).code).toBe("no_session");
  });

  it("ne marque pas « no_session » quand c'est l'API qui refuse", async () => {
    // La distinction décide du comportement du client : sans elle, il
    // réessaierait pour tout le monde, ou pour personne.
    callUpstream.mockResolvedValue({ ok: false, status: 401, data: { detail: "refusé" } });

    const response = await POST();

    expect((await response.json()).code).toBeUndefined();
  });
});
