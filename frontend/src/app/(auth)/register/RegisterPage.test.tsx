import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import RegisterPage from "./page";
import { renderWithProviders } from "@/test-utils";
import { TERMS_VERSION } from "@/content/conditions";

const { signUp, push } = vi.hoisted(() => ({ signUp: vi.fn(), push: vi.fn() }));

vi.mock("@/components/providers/AuthProvider", async () => {
  const actual = await vi.importActual<typeof import("@/components/providers/AuthProvider")>(
    "@/components/providers/AuthProvider"
  );
  return { ...actual, useAuth: () => ({ register: signUp }) };
});

vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));

async function remplirLeFormulaire() {
  await userEvent.type(screen.getByLabelText("Prénom"), "Awa");
  await userEvent.type(screen.getByLabelText("Nom"), "Traoré");
  await userEvent.type(screen.getByLabelText("Téléphone"), "+22670001111");
  await userEvent.type(screen.getByLabelText("Mot de passe"), "UnMotDePasseSolide9");
  await userEvent.type(
    screen.getByLabelText("Confirmer le mot de passe"),
    "UnMotDePasseSolide9"
  );
}

describe("Inscription", () => {
  beforeEach(() => {
    signUp.mockReset().mockResolvedValue(undefined);
    push.mockReset();
  });

  it("ne crée aucun compte tant que les conditions ne sont pas acceptées", async () => {
    renderWithProviders(<RegisterPage />);
    await remplirLeFormulaire();
    await userEvent.click(screen.getByRole("button", { name: "Créer mon compte" }));

    const alerte = await screen.findByRole("alert");
    expect(alerte).toHaveTextContent(/accepter les conditions/i);
    expect(signUp).not.toHaveBeenCalled();
  });

  it("part décochée : une case pré-cochée n'est pas un consentement", () => {
    renderWithProviders(<RegisterPage />);
    expect(screen.getByRole("checkbox")).not.toBeChecked();
  });

  it("envoie l'acceptation et la version du texte affiché", async () => {
    renderWithProviders(<RegisterPage />);
    await remplirLeFormulaire();
    await userEvent.click(screen.getByRole("checkbox"));
    await userEvent.click(screen.getByRole("button", { name: "Créer mon compte" }));

    await waitFor(() => expect(signUp).toHaveBeenCalledTimes(1));
    expect(signUp.mock.calls[0][0]).toMatchObject({
      accept_terms: true,
      terms_version: TERMS_VERSION,
    });
  });

  it("mène au texte, dans un onglet qui ne perd pas le formulaire rempli", () => {
    renderWithProviders(<RegisterPage />);
    const lien = screen.getByRole("link", { name: /conditions et la politique/i });
    expect(lien).toHaveAttribute("href", "/conditions");
    expect(lien).toHaveAttribute("target", "_blank");
  });
});
