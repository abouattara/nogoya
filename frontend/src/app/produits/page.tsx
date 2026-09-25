import { Suspense } from "react";
import { FiltersSidebar } from "@/components/search/FiltersSidebar";
import { ProductGrid } from "@/components/product/ProductGrid";
import { Pagination } from "@/components/search/Pagination";
import { Skeleton } from "@/components/ui/Feedback";
import { getCategories, getProducts, pickAttributeParams } from "@/lib/api";
import type { ListingType } from "@/lib/types";

export const dynamic = "force-dynamic";
export const metadata = { title: "Rechercher un article" };

interface SearchParams {
  [key: string]: string | undefined;
  search?: string;
  category?: string;
  city?: string;
  listing_type?: string;
  price_min?: string;
  price_max?: string;
  page?: string;
}

export default async function ProductsPage({ searchParams }: PageProps<"/produits">) {
  const params = (await searchParams) as SearchParams;

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
      <div className="flex flex-col gap-8 lg:flex-row">
        <Suspense fallback={<Skeleton className="h-96 w-64" />}>
          <FiltersSidebarData />
        </Suspense>
        <div className="flex-1">
          <Suspense fallback={<ResultsSkeleton />} key={JSON.stringify(params)}>
            <Results params={params} />
          </Suspense>
        </div>
      </div>
    </div>
  );
}

async function FiltersSidebarData() {
  const categories = await getCategories();
  return <FiltersSidebar categories={categories} />;
}

async function Results({ params }: { params: SearchParams }) {
  const page = Number(params.page ?? "1");
  const data = await getProducts({
    search: params.search,
    category: params.category,
    city: params.city,
    listing_type: params.listing_type as ListingType | undefined,
    price_min: params.price_min,
    price_max: params.price_max,
    ordering: "-created_at",
    page: params.page,
    attributes: pickAttributeParams(params),
  });

  return (
    <>
      <p className="mb-4 text-sm text-foreground-muted">{data.count} résultat{data.count > 1 ? "s" : ""}</p>
      <ProductGrid products={data.results} />
      <Pagination
        page={page}
        hasNext={Boolean(data.next)}
        hasPrevious={Boolean(data.previous)}
        basePath="/produits"
        searchParams={params}
      />
    </>
  );
}

function ResultsSkeleton() {
  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
      {Array.from({ length: 8 }).map((_, i) => (
        <Skeleton key={i} className="aspect-3/4" />
      ))}
    </div>
  );
}
