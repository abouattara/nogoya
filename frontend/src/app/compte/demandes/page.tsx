"use client";

import { useQuery } from "@tanstack/react-query";
import Image from "next/image";
import Link from "next/link";
import { Badge, EmptyState, ErrorState, Skeleton } from "@/components/ui/Feedback";
import { RequireAuth } from "@/components/providers/RequireAuth";
import { apiFetch } from "@/lib/client-api";
import { formatPrice } from "@/lib/format";
import type { Paginated, RentalRequest, RentalRequestStatus } from "@/lib/types";

/**
 * Où un client suit ses demandes.
 *
 * L'écran répond à une seule question : « où en est ma demande ? ». D'où un
 * libellé explicite par étape plutôt qu'un code de statut, et une phrase qui
 * dit ce qui se passe maintenant — l'attente est supportable quand on sait
 * ce qu'on attend.
 */

const STATUS_TONE: Record<RentalRequestStatus, "warning" | "brand" | "danger" | "neutral"> = {
  submitted: "warning",
  checking: "warning",
  available: "brand",
  unavailable: "danger",
  connected: "brand",
  cancelled: "neutral",
};

const STATUS_EXPLANATION: Record<RentalRequestStatus, string> = {
  submitted: "Nous avons bien reçu votre demande et contactons le propriétaire.",
  checking: "Nous vérifions la disponibilité auprès du propriétaire.",
  available: "Le bien est disponible pour vos dates. Nous vous mettons en relation.",
  unavailable: "Le propriétaire a indiqué que le bien n'est pas libre à ces dates.",
  connected: "Les coordonnées du propriétaire vous ont été transmises.",
  cancelled: "Vous avez annulé cette demande.",
};

export default function MyRentalRequestsPage() {
  return <RequireAuth>{() => <RequestList />}</RequireAuth>;
}

function RequestList() {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["my-rental-requests"],
    queryFn: () => apiFetch<Paginated<RentalRequest>>("/api/v1/rental-requests/"),
  });

  return (
    <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold">Mes demandes</h1>
        <Link href="/compte" className="text-sm text-brand-700 underline underline-offset-2">
          ← Mon compte
        </Link>
      </div>

      {isError ? (
        <ErrorState message="Impossible de charger vos demandes." retry={() => refetch()} />
      ) : isLoading ? (
        <div className="flex flex-col gap-3">
          <Skeleton className="h-28 w-full" />
          <Skeleton className="h-28 w-full" />
        </div>
      ) : !data || data.results.length === 0 ? (
        <EmptyState
          title="Aucune demande"
          description="Vos demandes de location apparaîtront ici, avec leur avancement."
        />
      ) : (
        <ul className="flex flex-col gap-3">
          {data.results.map((request) => (
            <li key={request.id} className="rounded-xl border border-border bg-surface p-4">
              <div className="flex gap-3">
                <div className="relative h-20 w-20 shrink-0 overflow-hidden rounded-lg bg-surface-muted">
                  {request.product.cover_image && (
                    <Image
                      src={request.product.cover_image}
                      alt={request.product.title}
                      fill
                      className="object-cover"
                      unoptimized
                    />
                  )}
                </div>

                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge tone={STATUS_TONE[request.status]}>{request.status_label}</Badge>
                    <span className="text-xs text-foreground-muted">
                      {formatDay(request.start_date)} → {formatDay(request.end_date)} ·{" "}
                      {request.nights} jour{request.nights > 1 ? "s" : ""}
                    </span>
                  </div>

                  <Link
                    href={`/produits/${request.product.slug}`}
                    className="mt-1 block truncate font-medium hover:underline"
                  >
                    {request.product.title}
                  </Link>
                  <p className="text-sm text-foreground-muted">
                    {request.product.city} · {formatPrice(request.product.price, request.product.currency)}
                  </p>

                  <p className="mt-2 text-sm text-foreground">
                    {STATUS_EXPLANATION[request.status]}
                  </p>

                  {request.thread && (
                    <Link
                      href={`/compte/messages/${request.thread}`}
                      className="mt-2 inline-block text-sm text-brand-700 underline underline-offset-2"
                    >
                      Voir les échanges
                    </Link>
                  )}
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function formatDay(iso: string) {
  return new Date(iso).toLocaleDateString("fr-FR", { day: "numeric", month: "short" });
}
