import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ProductCard } from "./ProductCard";
import { makeProduct, renderWithProviders } from "@/test-utils";

describe("ProductCard", () => {
  it("shows the title, city, price and rental period", () => {
    renderWithProviders(<ProductCard product={makeProduct()} />);

    expect(screen.getByText("Tente de réception")).toBeInTheDocument();
    expect(screen.getByText("Ouagadougou")).toBeInTheDocument();
    expect(screen.getByText(/25/)).toBeInTheDocument();
    expect(screen.getByText(/\/ jour/)).toBeInTheDocument();
  });

  it("labels a sale listing without a rental period", () => {
    renderWithProviders(
      <ProductCard product={makeProduct({ listing_type: "sale", rental_period: "none" })} />
    );

    expect(screen.getByText("Vente")).toBeInTheDocument();
    expect(screen.queryByText(/\/ jour/)).not.toBeInTheDocument();
  });

  it("links to the product detail page", () => {
    renderWithProviders(<ProductCard product={makeProduct()} />);

    expect(screen.getByRole("link")).toHaveAttribute("href", "/produits/tente-de-reception");
  });

  it("falls back to a placeholder when there is no photo", () => {
    renderWithProviders(<ProductCard product={makeProduct({ cover_image: null })} />);

    expect(screen.getByText("Pas de photo")).toBeInTheDocument();
  });

  it("exposes the favourite control with its current state", () => {
    renderWithProviders(<ProductCard product={makeProduct({ is_favorite: true })} />);

    const favorite = screen.getByRole("button", { name: /retirer des favoris/i });
    expect(favorite).toHaveAttribute("aria-pressed", "true");
  });
});
