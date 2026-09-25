import { apiGet, visitorHeaders } from "./server-api";
import type { Category, Paginated, ProductDetail, ProductFiltersQuery, ProductListItem, SupplierPublic } from "./types";

export function getCategories() {
  return apiGet<Category[]>("/api/v1/categories/");
}

export async function getProducts(query: ProductFiltersQuery) {
  return apiGet<Paginated<ProductListItem>>(
    "/api/v1/products/",
    {
      search: query.search,
      category: query.category,
      city: query.city,
      listing_type: query.listing_type,
      price_min: query.price_min,
      price_max: query.price_max,
      ordering: query.ordering,
      page: query.page,
      // Dynamic per-category filters (attr_<slug>, attr_<slug>_min/_max).
      ...(query.attributes ?? {}),
    },
    // The list endpoint logs the search: it must be attributed to this visitor.
    { headers: await visitorHeaders() }
  );
}

/** Extracts the `attr_*` entries the dynamic attribute filters rely on. */
export function pickAttributeParams(params: Record<string, string | undefined>) {
  return Object.fromEntries(
    Object.entries(params).filter(([key, value]) => key.startsWith("attr_") && value)
  ) as Record<string, string>;
}

export async function getProduct(slug: string) {
  // The retrieve endpoint records the view; the header keeps it attributed to
  // one visitor instead of inventing a new one on every render.
  return apiGet<ProductDetail>(`/api/v1/products/${slug}/`, undefined, {
    cache: "no-store",
    headers: await visitorHeaders(),
  });
}

export function getSupplier(id: string | number) {
  return apiGet<SupplierPublic>(`/api/v1/suppliers/${id}/`);
}

export function getSupplierProducts(id: string | number, query: ProductFiltersQuery = {}) {
  return apiGet<Paginated<ProductListItem>>("/api/v1/products/", {
    supplier: String(id),
    search: query.search,
    category: query.category,
    listing_type: query.listing_type,
    price_min: query.price_min,
    price_max: query.price_max,
    ordering: query.ordering,
    page: query.page,
  });
}
