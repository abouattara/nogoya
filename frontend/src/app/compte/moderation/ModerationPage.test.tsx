import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ModerationPage from "./page";
import { makeProduct, renderWithProviders } from "@/test-utils";
import type { ModerationProduct } from "@/lib/types";

const { apiFetch, FakeApiError } = vi.hoisted(() => ({
  apiFetch: vi.fn(),
  FakeApiError: class extends Error {
    status: number;
    body: unknown;
    constructor(status: number, body: unknown) {
      super("api");
      this.status = status;
      this.body = body;
    }
  },
}));
vi.mock("@/lib/client-api", () => ({ apiFetch, ApiError: FakeApiError }));

// RequireAuth lit le store d'authentification ; la session est posée ici.
vi.mock("@/components/providers/RequireAuth", () => ({
  RequireAuth: ({ children }: { children: (u: unknown) => React.ReactNode }) =>
    children({ id: 1, role: "visitor", full_name: "Équipe" }),
}));

function moderationProduct(overrides: Partial<ModerationProduct> = {}): ModerationProduct {
  return {
    ...makeProduct({ status: "pending", title: "Tente de réception" }),
    description: "Une tente spacieuse.",
    images: [],
    location: "Gounghin",
    region: "Centre",
    country: "Burkina Faso",
    category_name: "Tentes",
    source_url: "",
    last_checked_at: null,
    published_at: null,
    ...overrides,
  } as ModerationProduct;
}

function page(results: ModerationProduct[]) {
  return { count: results.length, next: null, previous: null, results };
}

describe("Page de modération", () => {
  beforeEach(() => {
    apiFetch.mockResolvedValue(page([moderationProduct()]));
  });

  it("demande par défaut les annonces qui attendent une décision", async () => {
    renderWithProviders(<ModerationPage />);

    await waitFor(() => expect(apiFetch).toHaveBeenCalled());
    const url = String(apiFetch.mock.calls[0][0]);
    expect(url).toContain("status=pending");
    expect(url).toContain("status=draft");
  });

  it("affiche toutes les photos, pas seulement la couverture", async () => {
    apiFetch.mockResolvedValue(
      page([
        moderationProduct({
          images: [
            { id: 1, image: "http://x/1.jpg", is_cover: true, order: 0, width: 800, height: 600 },
            { id: 2, image: "http://x/2.jpg", is_cover: false, order: 1, width: 800, height: 600 },
            { id: 3, image: "http://x/3.jpg", is_cover: false, order: 2, width: 800, height: 600 },
          ],
        }),
      ])
    );
    renderWithProviders(<ModerationPage />);

    // On refuse souvent une annonce sur sa deuxième image.
    await waitFor(() => expect(screen.getAllByRole("img")).toHaveLength(3));
  });

  it("publie une annonce et rafraîchit la file", async () => {
    renderWithProviders(<ModerationPage />);
    await screen.findByText("Tente de réception");

    apiFetch.mockClear();
    apiFetch.mockResolvedValue(page([]));
    await userEvent.click(screen.getByRole("button", { name: "Publier" }));

    await waitFor(() => {
      const decision = apiFetch.mock.calls.find((call: unknown[]) =>
        String(call[0]).includes("/moderate/")
      );
      expect(decision).toBeTruthy();
      const options = decision![1] as { body: string };
      expect(JSON.parse(options.body)).toEqual({ action: "approve" });
    });
  });

  it("ne propose pas de publier ce qui est déjà publié", async () => {
    apiFetch.mockResolvedValue(page([moderationProduct({ status: "approved" })]));
    renderWithProviders(<ModerationPage />);

    await screen.findByText("Tente de réception");
    expect(screen.queryByRole("button", { name: "Publier" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Refuser" })).toBeInTheDocument();
  });

  it("dit clairement qu'un compte sans droits ne peut pas décider", async () => {
    renderWithProviders(<ModerationPage />);
    await screen.findByText("Tente de réception");

    apiFetch.mockRejectedValue(new FakeApiError(403, { detail: "Réservé à l'équipe." }));
    await userEvent.click(screen.getByRole("button", { name: "Publier" }));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(/droits de modération/i);
  });

  it("renvoie vers la source d'une annonce référencée", async () => {
    apiFetch.mockResolvedValue(
      page([
        moderationProduct({
          provenance: "external_reference",
          source_name: "Agence Exemple",
          source_url: "https://exemple.test/a-1",
        }),
      ])
    );
    renderWithProviders(<ModerationPage />);

    const link = await screen.findByRole("link", { name: /annonce d'origine/i });
    expect(link).toHaveAttribute("href", "https://exemple.test/a-1");
    expect(link.getAttribute("rel")).toContain("noopener");
  });

  it("n'affiche aucune coordonnée du vendeur", async () => {
    apiFetch.mockResolvedValue(
      page([moderationProduct({ supplier_name: "Issa Ouédraogo" })])
    );
    const { container } = renderWithProviders(<ModerationPage />);

    await screen.findByText("Tente de réception");
    // Modérer ne demande pas de savoir qui joindre.
    expect(container.textContent).not.toMatch(/\+?\d{8,}/);
  });

  it("explique le refus de l'API plutôt que d'afficher une file vide", async () => {
    apiFetch.mockRejectedValue(new FakeApiError(403, { detail: "Réservé à l'équipe." }));
    renderWithProviders(<ModerationPage />);

    await waitFor(() =>
      expect(screen.getByText(/réservé à l'équipe/i)).toBeInTheDocument()
    );
  });

  it("change de file quand on clique un onglet", async () => {
    renderWithProviders(<ModerationPage />);
    await screen.findByText("Tente de réception");

    apiFetch.mockClear();
    await userEvent.click(screen.getByRole("tab", { name: "Publiées" }));

    await waitFor(() => {
      const url = String(apiFetch.mock.calls.at(-1)![0]);
      expect(url).toContain("status=approved");
      expect(url).not.toContain("status=pending");
    });
  });

  it("filtre par origine", async () => {
    renderWithProviders(<ModerationPage />);
    await screen.findByText("Tente de réception");

    apiFetch.mockClear();
    await userEvent.selectOptions(
      screen.getByLabelText("Filtrer par origine"),
      "external_reference"
    );

    await waitFor(() => {
      const url = String(apiFetch.mock.calls.at(-1)![0]);
      expect(url).toContain("provenance=external_reference");
    });
  });

  it("signale une annonce sans photo", async () => {
    renderWithProviders(<ModerationPage />);
    const card = (await screen.findByText("Tente de réception")).closest("li")!;
    expect(within(card).getByText(/Aucune photo/)).toBeInTheDocument();
  });
});
