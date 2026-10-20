import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ExternalListingCard } from "./ExternalListingCard";
import { ProductCard } from "./ProductCard";
import { makeProduct, renderWithProviders } from "@/test-utils";
import type { ProductDetail } from "@/lib/types";

function externalProduct(overrides: Partial<ProductDetail> = {}): ProductDetail {
  return {
    ...makeProduct({ provenance: "external_reference", source_name: "Agence Exemple" }),
    description: "Appartement meublé à Ouaga 2000.",
    supplier: null,
    images: [],
    published_at: "2026-10-20T10:00:00Z",
    category: null,
    location: "Ouaga 2000",
    region: "Centre",
    country: "Burkina Faso",
    latitude: null,
    longitude: null,
    location_precision: "approximate",
    map_url: null,
    attributes: [],
    source: { name: "Agence Exemple", reference_url: "https://exemple.test" },
    source_url: "https://exemple.test/annonces/a-1",
    last_checked_at: "2026-10-20T10:00:00Z",
    ...overrides,
  } as ProductDetail;
}

describe("ExternalListingCard", () => {
  it("renvoie vers l'annonce d'origine et nomme la source", () => {
    render(<ExternalListingCard product={externalProduct()} />);

    const link = screen.getByRole("link", { name: /voir l'annonce originale/i });
    expect(link).toHaveAttribute("href", "https://exemple.test/annonces/a-1");
    // Un lien vers un tiers ne doit ni ouvrir l'acces a notre fenetre ni
    // lui transmettre notre referencement.
    expect(link.getAttribute("rel")).toContain("noopener");
    expect(link.getAttribute("rel")).toContain("nofollow");
    expect(screen.getByText(/Publiée par Agence Exemple/)).toBeInTheDocument();
  });

  it("ne propose aucun parcours de réservation ou de contact NOGOYA", () => {
    render(<ExternalListingCard product={externalProduct()} />);

    expect(screen.queryByRole("button", { name: /réserver/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /voir le numéro/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /envoyer un message/i })).not.toBeInTheDocument();
  });

  it("affiche la date de dernière vérification", () => {
    render(<ExternalListingCard product={externalProduct()} />);
    expect(screen.getByText(/Dernière vérification/)).toBeInTheDocument();
  });

  it("le dit plutôt que d'afficher un lien mort quand l'URL manque", () => {
    render(<ExternalListingCard product={externalProduct({ source_url: "" })} />);

    expect(screen.queryByRole("link", { name: /voir l'annonce originale/i })).not.toBeInTheDocument();
    expect(screen.getByText(/pas disponible/i)).toBeInTheDocument();
  });
});

describe("ProductCard — provenance", () => {
  it("signale une annonce référencée dès la liste", () => {
    renderWithProviders(
      <ProductCard
        product={makeProduct({ provenance: "external_reference", source_name: "Agence Exemple" })}
      />
    );
    expect(screen.getByText(/Annonce référencée · Agence Exemple/)).toBeInTheDocument();
  });

  it("n'ajoute rien pour une annonce gérée par NOGOYA", () => {
    renderWithProviders(<ProductCard product={makeProduct()} />);
    expect(screen.queryByText(/Annonce référencée/)).not.toBeInTheDocument();
  });
});
