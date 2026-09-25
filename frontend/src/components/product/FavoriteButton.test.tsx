import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { FavoriteButton } from "./FavoriteButton";
import { renderWithProviders } from "@/test-utils";
import { useAuthStore } from "@/store/auth-store";

import { routerMock } from "../../../vitest.setup";

const apiFetch = vi.hoisted(() => vi.fn());
vi.mock("@/lib/client-api", () => ({
  apiFetch,
  ApiError: class extends Error {},
}));

function signIn() {
  useAuthStore.setState({
    user: { id: 1, role: "visitor", full_name: "Fatou" },
    accessToken: "token",
    status: "ready",
  });
}

/** Answers the favourites lookup with `slugs`, the toggle with `toggled`. */
function mockApi({ slugs = [] as string[], toggled = true } = {}) {
  apiFetch.mockImplementation(async (path: string) => {
    if (path === "/api/v1/favorites/slugs/") return { slugs };
    return { is_favorite: toggled };
  });
}

describe("FavoriteButton", () => {
  beforeEach(() => {
    useAuthStore.setState({ user: null, accessToken: null, status: "ready" });
  });

  it("sends anonymous users to the login page instead of calling the API", async () => {
    renderWithProviders(<FavoriteButton slug="tente" initial={false} />);

    await userEvent.click(screen.getByRole("button"));

    expect(routerMock.push).toHaveBeenCalledWith("/login");
    expect(apiFetch).not.toHaveBeenCalled();
  });

  it("adds to favourites and reflects the server's answer", async () => {
    signIn();
    mockApi({ toggled: true });

    renderWithProviders(<FavoriteButton slug="tente" initial={false} />);
    await userEvent.click(screen.getByRole("button", { name: /ajouter aux favoris/i }));

    expect(apiFetch).toHaveBeenCalledWith("/api/v1/products/tente/toggle_favorite/", {
      method: "POST",
    });
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /retirer des favoris/i })).toHaveAttribute(
        "aria-pressed",
        "true"
      )
    );
  });

  it("shows an already-saved listing as saved, although the SSR markup says otherwise", async () => {
    // The server-side fetch is anonymous, so `initial` is false even for a
    // listing this user saved. Trusting it made the heart look empty — and
    // the next click silently *removed* the favourite.
    signIn();
    mockApi({ slugs: ["tente"] });

    renderWithProviders(<FavoriteButton slug="tente" initial={false} variant="button" />);

    await waitFor(() =>
      expect(screen.getByRole("button", { name: /retirer des favoris/i })).toHaveAttribute(
        "aria-pressed",
        "true"
      )
    );
    expect(screen.getByText("Dans vos favoris")).toBeInTheDocument();
  });

  it("leaves other listings untouched", async () => {
    signIn();
    mockApi({ slugs: ["un-autre-produit"] });

    renderWithProviders(<FavoriteButton slug="tente" initial={false} variant="button" />);

    await waitFor(() => expect(apiFetch).toHaveBeenCalledWith("/api/v1/favorites/slugs/"));
    expect(screen.getByRole("button", { name: /ajouter aux favoris/i })).toHaveAttribute(
      "aria-pressed",
      "false"
    );
  });

  it("rolls the optimistic update back when the request fails", async () => {
    signIn();
    apiFetch.mockImplementation(async (path: string) => {
      if (path === "/api/v1/favorites/slugs/") return { slugs: [] };
      throw new Error("network");
    });

    renderWithProviders(<FavoriteButton slug="tente" initial={false} />);
    await userEvent.click(screen.getByRole("button"));

    await waitFor(() =>
      expect(screen.getByRole("button", { name: /ajouter aux favoris/i })).toHaveAttribute(
        "aria-pressed",
        "false"
      )
    );
  });

  it("renders a labelled button in the detail-page variant", () => {
    signIn();
    mockApi();
    renderWithProviders(<FavoriteButton slug="tente" initial variant="button" />);

    expect(screen.getByText("Dans vos favoris")).toBeInTheDocument();
  });
});
