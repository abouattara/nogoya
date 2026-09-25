"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { ButtonLink } from "@/components/ui/Button";
import { EmptyState, Skeleton } from "@/components/ui/Feedback";
import { ProductGrid } from "@/components/product/ProductGrid";
import { apiFetch } from "@/lib/client-api";
import type { ProductListItem } from "@/lib/types";

interface DiscoveryPayload {
  recently_viewed: ProductListItem[];
  recommended: ProductListItem[];
  new_arrivals: ProductListItem[];
  recent_searches: Array<{
    query: string;
    normalized_query: string;
    results_count: number;
    created_at: string;
  }>;
}

/**
 * Personalised blocks for the signed-in home/account page: history,
 * suggestions and new arrivals, all derived from what the visitor browsed.
 */
export function DiscoverySections() {
  const { data, isLoading } = useQuery({
    queryKey: ["discovery"],
    queryFn: () => apiFetch<DiscoveryPayload>("/api/v1/discovery/me/", { auth: true }),
  });

  if (isLoading) {
    return <Skeleton className="h-64 w-full" />;
  }

  if (!data) return null;

  const nothingYet =
    data.recently_viewed.length === 0 &&
    data.recommended.length === 0 &&
    data.new_arrivals.length === 0;

  if (nothingYet) {
    return (
      <EmptyState
        title="Commencez à explorer"
        description="Parcourez quelques annonces : vos suggestions apparaîtront ici."
        action={<ButtonLink href="/produits">Voir les annonces</ButtonLink>}
      />
    );
  }

  return (
    <div className="flex flex-col gap-10">
      {data.recent_searches.length > 0 && (
        <section>
          <h2 className="mb-3 text-lg font-semibold">Reprendre votre recherche</h2>
          <ul className="flex flex-wrap gap-2">
            {data.recent_searches.map((search) => (
              <li key={search.normalized_query}>
                <Link
                  href={`/produits?search=${encodeURIComponent(search.query)}`}
                  className="inline-flex items-center gap-2 rounded-full border border-border bg-surface px-3 py-1.5 text-sm hover:bg-surface-muted"
                >
                  <span aria-hidden="true">🔎</span>
                  {search.query}
                  <span className="text-xs text-foreground-muted">
                    {search.results_count} résultat{search.results_count > 1 ? "s" : ""}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}

      {data.recently_viewed.length > 0 && (
        <DiscoveryBlock title="Vus récemment" products={data.recently_viewed} />
      )}
      {data.recommended.length > 0 && (
        <DiscoveryBlock
          title="Continuer votre découverte"
          subtitle="À partir des annonces que vous avez consultées"
          products={data.recommended}
        />
      )}
      {data.new_arrivals.length > 0 && (
        <DiscoveryBlock title="Nouveautés" products={data.new_arrivals} />
      )}
    </div>
  );
}

function DiscoveryBlock({
  title,
  subtitle,
  products,
}: {
  title: string;
  subtitle?: string;
  products: ProductListItem[];
}) {
  return (
    <section>
      <div className="mb-3">
        <h2 className="text-lg font-semibold">{title}</h2>
        {subtitle && <p className="text-sm text-foreground-muted">{subtitle}</p>}
      </div>
      <ProductGrid products={products} />
    </section>
  );
}
