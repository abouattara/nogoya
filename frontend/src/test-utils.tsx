import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, type RenderOptions } from "@testing-library/react";
import type { ReactElement, ReactNode } from "react";
import type {
  Category,
  CategoryAttribute,
  Message,
  MessageAttachment,
  ProductListItem,
  SeriesPoint,
} from "@/lib/types";

export function renderWithProviders(ui: ReactElement, options?: RenderOptions) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  }
  return { client, ...render(ui, { wrapper: Wrapper, ...options }) };
}

export function makeProduct(overrides: Partial<ProductListItem> = {}): ProductListItem {
  return {
    id: 1,
    title: "Tente de réception",
    slug: "tente-de-reception",
    category: "tentes",
    price: "25000",
    currency: "XOF",
    listing_type: "rent",
    rental_period: "day",
    city: "Ouagadougou",
    cover_image: "http://127.0.0.1:8000/media/products/tente.jpg",
    views_count: 42,
    shares_count: 3,
    supplier_name: "Issa Ouédraogo",
    status: "approved",
    is_active: true,
    is_favorite: false,
    created_at: "2026-09-01T10:00:00Z",
    ...overrides,
  };
}

export function makeAttribute(overrides: Partial<CategoryAttribute> = {}): CategoryAttribute {
  return {
    id: 1,
    name: "Marque",
    slug: "marque",
    attribute_type: "text",
    required: false,
    filterable: false,
    searchable: false,
    unit: "",
    options: [],
    position: 0,
    ...overrides,
  };
}

export function makeCategory(overrides: Partial<Category> = {}): Category {
  return {
    id: 1,
    name: "Voitures",
    slug: "voitures",
    icon: "",
    order: 0,
    parent: null,
    children: [],
    attributes: [],
    ...overrides,
  };
}

export function makeMessage(overrides: Partial<Message> = {}): Message {
  return {
    id: 1,
    conversation: 1,
    sender: {
      id: 2,
      full_name: "Fatou Kaboré",
      avatar: null,
      role: "visitor",
      created_at: "2026-09-01T10:00:00Z",
    },
    message_type: "text",
    body: "Bonjour",
    shared_product: null,
    attachments: [],
    created_at: "2026-09-20T10:00:00Z",
    read_at: null,
    is_mine: false,
    ...overrides,
  };
}

export function makeAttachment(
  overrides: Partial<MessageAttachment> = {}
): MessageAttachment {
  return {
    id: 1,
    kind: "image",
    status: "ready",
    url: "http://127.0.0.1:8000/api/v1/conversations/1/messages/1/attachments/1/",
    poster_url: "http://127.0.0.1:8000/api/v1/conversations/1/messages/1/attachments/1/poster/",
    mime_type: "image/jpeg",
    size: 120_000,
    width: 900,
    height: 600,
    duration: 0,
    ...overrides,
  };
}

export function makeSeries(values: number[]): SeriesPoint[] {
  return values.map((value, index) => ({
    date: `2026-09-${String(index + 1).padStart(2, "0")}`,
    value,
  }));
}
