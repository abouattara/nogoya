"use client";

import { useQuery } from "@tanstack/react-query";
import { ButtonLink } from "@/components/ui/Button";
import { EmptyState, ErrorState, Skeleton } from "@/components/ui/Feedback";
import { ProductGrid } from "@/components/product/ProductGrid";
import { RequireAuth } from "@/components/providers/RequireAuth";
import { apiFetch } from "@/lib/client-api";
import type { Favorite, Paginated } from "@/lib/types";

export default function FavoritesPage() {
  return (
    <RequireAuth>
      {() => (
        <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
          <h1 className="mb-6 text-2xl font-bold">Mes favoris</h1>
          <FavoritesList />
        </div>
      )}
    </RequireAuth>
  );
}

function FavoritesList() {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["favorites"],
    queryFn: () => apiFetch<Paginated<Favorite>>("/api/v1/favorites/"),
  });

  if (isLoading) return <Skeleton className="h-96 w-full" />;
  if (isError || !data) return <ErrorState message="Impossible de charger vos favoris." retry={refetch} />;

  if (data.results.length === 0) {
    return (
      <EmptyState
        title="Aucun favori pour l'instant"
        description="Touchez le cœur sur une annonce pour la retrouver ici plus tard."
        action={<ButtonLink href="/produits">Parcourir les annonces</ButtonLink>}
      />
    );
  }

  return (
    <>
      <p className="mb-4 text-sm text-foreground-muted">
        {data.count} annonce{data.count > 1 ? "s" : ""} enregistrée{data.count > 1 ? "s" : ""}
      </p>
      <ProductGrid products={data.results.map((favorite) => favorite.product)} />
    </>
  );
}
