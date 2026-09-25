"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import Image from "next/image";
import Link from "next/link";
import { useState } from "react";
import { Badge, EmptyState, ErrorState, Skeleton } from "@/components/ui/Feedback";
import { Button, ButtonLink } from "@/components/ui/Button";
import { RequireAuth } from "@/components/providers/RequireAuth";
import { SupplierAnalyticsPanel } from "@/components/charts/SupplierAnalyticsPanel";
import { apiFetch, ApiError } from "@/lib/client-api";
import { formatPrice } from "@/lib/format";
import type { Paginated, ProductListItem, ProductStatus, SupplierStats } from "@/lib/types";

const STATUS_LABEL: Record<ProductStatus, { label: string; tone: "warning" | "brand" | "danger" }> = {
  pending: { label: "En attente de modération", tone: "warning" },
  approved: { label: "Approuvée", tone: "brand" },
  rejected: { label: "Rejetée", tone: "danger" },
};

export default function SupplierDashboardPage() {
  return (
    <RequireAuth role="supplier">
      {() => (
        <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
          <div className="mb-6 flex items-center justify-between">
            <h1 className="text-2xl font-bold">Tableau de bord fournisseur</h1>
            <div className="flex items-center gap-3">
              <Link href="/compte/fournisseur/parametres" className="text-sm font-medium text-brand-dark hover:underline">
                Paramètres
              </Link>
              <ButtonLink href="/compte/fournisseur/produits/nouveau">+ Publier une annonce</ButtonLink>
            </div>
          </div>
          <StatsHeader />
          <div className="mt-8">
            <SupplierAnalyticsPanel />
          </div>
          <h2 className="mb-4 mt-8 text-lg font-semibold">Mes annonces</h2>
          <ProductsTable />
        </div>
      )}
    </RequireAuth>
  );
}

function StatsHeader() {
  const { data, isLoading } = useQuery({
    queryKey: ["supplier-stats"],
    queryFn: () => apiFetch<SupplierStats>("/api/v1/suppliers/me/stats/"),
  });

  const tiles = [
    { label: "Produits en ligne", value: data?.products_online },
    { label: "Vues totales", value: data?.total_views },
    { label: "Contacts", value: data?.total_contacts },
    { label: "Messages non lus", value: data?.unread_messages },
  ];

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      {tiles.map((tile) => (
        <div key={tile.label} className="rounded-xl border border-border bg-surface p-4">
          <p className="text-2xl font-bold text-brand-700">{isLoading ? "—" : tile.value}</p>
          <p className="text-xs text-foreground-muted">{tile.label}</p>
        </div>
      ))}
    </div>
  );
}

function ProductsTable() {
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["my-products"],
    queryFn: () => apiFetch<Paginated<ProductListItem>>("/api/v1/products/?mine=true"),
  });

  async function toggleActive(slug: string) {
    setError(null);
    try {
      await apiFetch(`/api/v1/products/${slug}/toggle_active/`, { method: "POST" });
      queryClient.invalidateQueries({ queryKey: ["my-products"] });
    } catch (err) {
      setError(err instanceof ApiError ? String((err.body as { detail?: string })?.detail ?? "Action impossible.") : "Action impossible.");
    }
  }

  async function remove(slug: string) {
    if (!confirm("Supprimer définitivement cette annonce ?")) return;
    await apiFetch(`/api/v1/products/${slug}/`, { method: "DELETE" });
    queryClient.invalidateQueries({ queryKey: ["my-products"] });
  }

  if (isLoading) return <Skeleton className="h-80 w-full" />;
  if (isError || !data) return <ErrorState message="Impossible de charger vos annonces." retry={refetch} />;
  if (data.results.length === 0) {
    return (
      <EmptyState
        title="Aucune annonce pour le moment"
        description="Publiez votre premier article pour qu'il apparaisse ici."
        action={<ButtonLink href="/compte/fournisseur/produits/nouveau">Publier une annonce</ButtonLink>}
      />
    );
  }

  return (
    <div className="overflow-hidden rounded-xl border border-border">
      {error && <p className="border-b border-danger-fg/20 bg-danger-bg px-4 py-2 text-sm text-danger-fg">{error}</p>}
      <table className="w-full text-sm">
        <thead className="bg-surface-muted text-left text-xs uppercase text-foreground-muted">
          <tr>
            <th className="px-4 py-3">Annonce</th>
            <th className="px-4 py-3">Statut</th>
            <th className="px-4 py-3">Vues</th>
            <th className="px-4 py-3">Actions</th>
          </tr>
        </thead>
        <tbody>
          {data.results.map((product) => (
            <tr key={product.id} className="border-t border-border">
              <td className="flex items-center gap-3 px-4 py-3">
                <div className="relative h-12 w-16 shrink-0 overflow-hidden rounded-md bg-surface-muted">
                  {product.cover_image && <Image src={product.cover_image} alt="" fill className="object-cover" />}
                </div>
                <div>
                  <p className="font-medium">{product.title}</p>
                  <p className="text-xs text-foreground-muted">{formatPrice(product.price, product.currency)}</p>
                </div>
              </td>
              <td className="px-4 py-3">
                <div className="flex flex-col gap-1">
                  <Badge tone={STATUS_LABEL[product.status].tone}>{STATUS_LABEL[product.status].label}</Badge>
                  {product.status === "approved" && (
                    <Badge tone={product.is_active ? "brand" : "neutral"}>{product.is_active ? "Publiée" : "Dépubliée"}</Badge>
                  )}
                </div>
              </td>
              <td className="px-4 py-3">{product.views_count}</td>
              <td className="px-4 py-3">
                <div className="flex flex-wrap gap-2">
                  <Link href={`/produits/${product.slug}`} className="text-brand-dark hover:underline">
                    Voir
                  </Link>
                  <Link href={`/compte/fournisseur/produits/${product.slug}/modifier`} className="text-brand-dark hover:underline">
                    Modifier
                  </Link>
                  {product.status === "approved" && (
                    <Button variant="secondary" size="sm" onClick={() => toggleActive(product.slug)}>
                      {product.is_active ? "Dépublier" : "Publier"}
                    </Button>
                  )}
                  <Button variant="danger" size="sm" onClick={() => remove(product.slug)}>
                    Supprimer
                  </Button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
