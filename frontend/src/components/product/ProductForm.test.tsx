import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ProductForm } from "./ProductForm";
import { makeAttribute, makeCategory, renderWithProviders } from "@/test-utils";

// vi.mock is hoisted, so both the spy and the error class must be created
// with vi.hoisted to exist by the time the factory runs.
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

const CATEGORIES = [
  makeCategory({
    id: 1,
    name: "Véhicules",
    slug: "vehicules",
    children: [
      makeCategory({
        id: 2,
        name: "Voitures",
        slug: "voitures",
        parent: 1,
        attributes: [
          makeAttribute({ id: 10, name: "Marque", slug: "marque", required: true }),
          makeAttribute({
            id: 11,
            name: "Carburant",
            slug: "carburant",
            attribute_type: "select",
            options: ["Essence", "Diesel"],
          }),
        ],
      }),
    ],
  }),
];

describe("ProductForm", () => {
  beforeEach(() => {
    apiFetch.mockImplementation((path: string) => {
      if (path.includes("/categories/")) return Promise.resolve(CATEGORIES);
      return Promise.resolve({ slug: "nouvelle-annonce" });
    });
  });

  it("blocks submission until the required fields are valid", async () => {
    renderWithProviders(<ProductForm mode="create" />);

    await userEvent.click(screen.getByRole("button", { name: /publier l'annonce/i }));

    await waitFor(() => expect(screen.getByText("Titre trop court")).toBeInTheDocument());
    expect(apiFetch).not.toHaveBeenCalledWith("/api/v1/products/", expect.anything());
  });

  it("requires at least one photo when creating", async () => {
    renderWithProviders(<ProductForm mode="create" />);

    await userEvent.type(screen.getByLabelText(/titre de l'annonce/i), "Berline confortable");
    await userEvent.type(screen.getByLabelText(/description/i), "Une belle berline familiale");
    await userEvent.type(screen.getByLabelText(/^prix$/i), "4500");
    await userEvent.type(screen.getByLabelText(/^ville$/i), "Ouagadougou");
    await waitFor(() => screen.getByRole("option", { name: /voitures/i }));
    await userEvent.selectOptions(screen.getByLabelText(/catégorie/i), "2");

    await userEvent.click(screen.getByRole("button", { name: /publier l'annonce/i }));

    await waitFor(() =>
      expect(screen.getByText("Ajoutez au moins une photo.")).toBeInTheDocument()
    );
  });

  it("shows the attributes of the selected category only", async () => {
    renderWithProviders(<ProductForm mode="create" />);

    await waitFor(() => screen.getByRole("option", { name: /voitures/i }));
    expect(screen.queryByLabelText(/marque/i)).not.toBeInTheDocument();

    await userEvent.selectOptions(screen.getByLabelText(/catégorie/i), "2");

    expect(await screen.findByLabelText("Marque *")).toBeInTheDocument();
    expect(screen.getByLabelText("Carburant")).toBeInTheDocument();
  });

  it("maps a server-side attribute error back onto its field", async () => {
    renderWithProviders(
      <ProductForm
        mode="edit"
        product={
          {
            id: 7,
            slug: "berline",
            title: "Berline",
            description: "Une belle berline familiale",
            price: "4500",
            currency: "XOF",
            listing_type: "sale",
            rental_period: "none",
            city: "Ouagadougou",
            location: "",
            region: "",
            country: "Burkina Faso",
            latitude: null,
            longitude: null,
            location_precision: "approximate",
            map_url: null,
            category: CATEGORIES[0].children[0],
            images: [],
            attributes: [],
            supplier: {
              id: 1,
              user: { id: 1, full_name: "Issa", avatar: null, role: "supplier", created_at: "" },
              city: "",
              bio: "",
              is_verified: false,
              rating_avg: "0",
              products_count: 0,
              phone: null,
              whatsapp_number: null,
              created_at: "",
            },
            published_at: null,
            cover_image: null,
            views_count: 0,
            shares_count: 0,
            supplier_name: "Issa",
            status: "approved",
            is_active: true,
            is_favorite: false,
            created_at: "",
          } as never
        }
      />
    );

    await waitFor(() => screen.getByLabelText("Marque *"));

    apiFetch.mockImplementation((path: string) => {
      if (path.includes("/categories/")) return Promise.resolve(CATEGORIES);
      return Promise.reject(
        new FakeApiError(400, { attributes: { marque: "« Marque » est obligatoire." } })
      );
    });

    await userEvent.click(screen.getByRole("button", { name: /enregistrer les modifications/i }));

    await waitFor(() =>
      expect(screen.getByText("« Marque » est obligatoire.")).toBeInTheDocument()
    );
    expect(screen.getByText("Vérifiez les caractéristiques de l'annonce.")).toBeInTheDocument();
  });
});
