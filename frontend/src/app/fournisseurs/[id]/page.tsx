import { Suspense } from "react";
import { notFound } from "next/navigation";
import { Badge, Skeleton } from "@/components/ui/Feedback";
import { ProductGrid } from "@/components/product/ProductGrid";
import { Pagination } from "@/components/search/Pagination";
import { SupplierCatalogControls } from "@/components/search/SupplierCatalogControls";
import { getSupplier, getSupplierProducts } from "@/lib/api";
import { ApiError } from "@/lib/server-api";
import { formatDate } from "@/lib/format";

export const dynamic = "force-dynamic";

export async function generateMetadata({ params }: PageProps<"/fournisseurs/[id]">) {
  const { id } = await params;
  try {
    const supplier = await getSupplier(id);
    return { title: supplier.user.full_name };
  } catch {
    return { title: "Fournisseur" };
  }
}

interface SearchParams {
  [key: string]: string | undefined;
  search?: string;
  category?: string;
  price_min?: string;
  price_max?: string;
  ordering?: string;
  page?: string;
}

export default async function SupplierPage({ params, searchParams }: PageProps<"/fournisseurs/[id]">) {
  const { id } = await params;
  const query = (await searchParams) as SearchParams;

  let supplier;
  try {
    supplier = await getSupplier(id);
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) notFound();
    throw err;
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
      <div className="flex flex-col items-start gap-4 rounded-2xl border border-border p-6 sm:flex-row sm:items-center">
        <div className="flex h-16 w-16 items-center justify-center rounded-full bg-brand-100 text-xl font-semibold text-brand-dark">
          {supplier.user.full_name.slice(0, 1).toUpperCase()}
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold">{supplier.user.full_name}</h1>
            {supplier.is_verified && <Badge tone="brand">Vérifié</Badge>}
          </div>
          <p className="text-sm text-foreground-muted">
            {supplier.city || "Localisation non précisée"} · Membre depuis {formatDate(supplier.created_at)}
          </p>
          {supplier.bio && <p className="mt-2 max-w-2xl text-sm text-foreground-muted">{supplier.bio}</p>}
        </div>
        <div className="flex gap-6 text-center">
          <div>
            <p className="text-lg font-semibold">{supplier.products_count}</p>
            <p className="text-xs text-foreground-muted">Annonces</p>
          </div>
        </div>
      </div>

      <div className="mt-8">
        <h2 className="mb-4 text-lg font-semibold">Catalogue</h2>
        <Suspense fallback={<Skeleton className="h-20 w-full" />}>
          <SupplierCatalogControls basePath={`/fournisseurs/${id}`} />
        </Suspense>
        <div className="mt-6">
          <Suspense fallback={<Skeleton className="h-96 w-full" />} key={JSON.stringify(query)}>
            <SupplierProducts id={id} query={query} />
          </Suspense>
        </div>
      </div>
    </div>
  );
}

async function SupplierProducts({ id, query }: { id: string; query: SearchParams }) {
  const page = Number(query.page ?? "1");
  const products = await getSupplierProducts(id, {
    search: query.search,
    category: query.category,
    price_min: query.price_min,
    price_max: query.price_max,
    ordering: query.ordering || "-created_at",
    page: query.page,
  });

  return (
    <>
      <p className="mb-4 text-sm text-foreground-muted">
        {products.count} résultat{products.count > 1 ? "s" : ""}
      </p>
      <ProductGrid products={products.results} emptyMessage="Ce fournisseur n'a pas encore d'annonce active." />
      <Pagination
        page={page}
        hasNext={Boolean(products.next)}
        hasPrevious={Boolean(products.previous)}
        basePath={`/fournisseurs/${id}`}
        searchParams={query}
      />
    </>
  );
}
