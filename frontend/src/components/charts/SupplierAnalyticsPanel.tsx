"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import clsx from "clsx";
import { ErrorState, Skeleton } from "@/components/ui/Feedback";
import { apiFetch } from "@/lib/client-api";
import type { SupplierAnalytics } from "@/lib/types";
import { BarList } from "./BarList";
import { LineChart } from "./LineChart";

const RANGES = [
  { label: "7 jours", days: 7 },
  { label: "30 jours", days: 30 },
  { label: "90 jours", days: 90 },
];

export function SupplierAnalyticsPanel() {
  const [days, setDays] = useState(30);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["supplier-analytics", days],
    queryFn: () => apiFetch<SupplierAnalytics>(`/api/v1/suppliers/me/analytics/?days=${days}`),
  });

  return (
    <section className="rounded-xl border border-border p-4 sm:p-6">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-lg font-semibold">Statistiques</h2>
        <div className="flex gap-2">
          {RANGES.map((range) => (
            <button
              key={range.days}
              onClick={() => setDays(range.days)}
              aria-pressed={days === range.days}
              className={clsx(
                "rounded-lg border px-3 py-1 text-sm transition-colors",
                days === range.days
                  ? "border-brand-300 bg-brand-50 font-medium text-brand-800"
                  : "border-border bg-surface text-foreground hover:bg-surface-muted"
              )}
            >
              {range.label}
            </button>
          ))}
        </div>
      </div>

      {isLoading && <Skeleton className="h-64 w-full" />}
      {isError && <ErrorState message="Impossible de charger vos statistiques." retry={refetch} />}

      {data && (
        <div className="flex flex-col gap-6">
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
            <LineChart data={data.views} label="Vues" />
            <LineChart data={data.contacts} label="Contacts" />
            <LineChart data={data.messages} label="Messages reçus" />
          </div>

          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
            <BarList
              title="Répartition des annonces"
              items={[
                { label: "En ligne", value: data.products_breakdown.online },
                { label: "Dépubliées", value: data.products_breakdown.unpublished },
                { label: "En modération", value: data.products_breakdown.pending },
                { label: "Rejetées", value: data.products_breakdown.rejected },
              ]}
            />
            <BarList
              title="Annonces les plus consultées"
              unit="vues"
              items={data.top_products.map((product) => ({
                label: product.title,
                value: product.views_count,
                href: `/produits/${product.slug}`,
              }))}
            />
            <BarList
              title="Vos catégories"
              unit="annonces"
              items={data.top_categories.map((category) => ({
                label: category.name,
                value: category.products,
              }))}
            />
          </div>
        </div>
      )}
    </section>
  );
}
