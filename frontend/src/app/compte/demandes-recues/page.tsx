"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Badge, EmptyState, ErrorState, Skeleton } from "@/components/ui/Feedback";
import { RequireAuth } from "@/components/providers/RequireAuth";
import { apiFetch, ApiError } from "@/lib/client-api";
import { formatPrice } from "@/lib/format";
import type { Paginated, RentalRequestStatus, StaffRentalRequest } from "@/lib/types";

/**
 * La file des demandes, côté équipe.
 *
 * Elle existe parce que les demandes des **visiteurs sans compte**
 * n'arrivaient nulle part : sans compte il n'y a pas de fil, et rien ne les
 * signalait ailleurs que dans l'administration Django. Or ce sont
 * précisément les demandes qu'il ne faut pas rater — personne ne relancera.
 *
 * L'écran montre les deux au même endroit, avec le numéro à rappeler bien
 * en vue : c'est le seul geste à faire.
 */

const QUEUES: { key: string; label: string; status?: RentalRequestStatus }[] = [
  { key: "a-traiter", label: "À traiter", status: "submitted" },
  { key: "en-cours", label: "En vérification", status: "checking" },
  { key: "disponibles", label: "Disponibles", status: "available" },
  { key: "faites", label: "Mises en relation", status: "connected" },
  { key: "toutes", label: "Toutes" },
];

const STATUS_TONE: Record<RentalRequestStatus, "warning" | "brand" | "danger" | "neutral"> = {
  submitted: "warning",
  checking: "warning",
  available: "brand",
  unavailable: "danger",
  connected: "brand",
  cancelled: "neutral",
};

export default function StaffRequestsPage() {
  return <RequireAuth>{() => <Queue />}</RequireAuth>;
}

function Queue() {
  const queryClient = useQueryClient();
  const [queue, setQueue] = useState(QUEUES[0]);
  const [busy, setBusy] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const query = queue.status ? `?status=${queue.status}` : "";
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["staff-rental-requests", query],
    queryFn: () => apiFetch<Paginated<StaffRentalRequest>>(`/api/v1/rental-requests/${query}`),
    staleTime: 10_000,
  });

  async function act(request: StaffRentalRequest, route: string) {
    setBusy(request.id);
    setError(null);
    try {
      await apiFetch(`/api/v1/rental-requests/${request.id}/${route}/`, { method: "POST" });
      await queryClient.invalidateQueries({ queryKey: ["staff-rental-requests"] });
    } catch (err) {
      if (err instanceof ApiError) {
        const body = err.body as { detail?: string } | null;
        setError(body?.detail ?? `Action refusée (erreur ${err.status}).`);
      } else {
        setError("Connexion interrompue : rien n'a été enregistré.");
      }
    } finally {
      setBusy(null);
    }
  }

  if (isError) {
    return (
      <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
        <ErrorState
          message="Impossible de charger les demandes. Cet écran est réservé à l'équipe."
          retry={() => refetch()}
        />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Demandes de location</h1>
          <p className="mt-1 text-sm text-foreground-muted">
            Vérifiez la disponibilité auprès du propriétaire, puis transmettez ses coordonnées.
          </p>
        </div>
        <Link href="/compte" className="text-sm text-brand-700 underline underline-offset-2">
          ← Mon compte
        </Link>
      </div>

      <div className="mb-5 flex flex-wrap gap-2" role="tablist" aria-label="Files de demandes">
        {QUEUES.map((item) => (
          <button
            key={item.key}
            type="button"
            role="tab"
            aria-selected={queue.key === item.key}
            onClick={() => setQueue(item)}
            className={
              queue.key === item.key
                ? "rounded-full bg-brand-600 px-4 py-1.5 text-sm font-medium text-white"
                : "rounded-full border border-border px-4 py-1.5 text-sm text-foreground-muted hover:bg-surface-muted"
            }
          >
            {item.label}
          </button>
        ))}
      </div>

      {error && (
        <p role="alert" className="mb-4 text-sm text-danger-fg">
          {error}
        </p>
      )}

      {isLoading ? (
        <div className="flex flex-col gap-3">
          <Skeleton className="h-36 w-full" />
          <Skeleton className="h-36 w-full" />
        </div>
      ) : !data || data.results.length === 0 ? (
        <EmptyState title="Rien à traiter" description="Aucune demande dans cette file." />
      ) : (
        <ul className="flex flex-col gap-4">
          {data.results.map((request) => (
            <RequestCard
              key={request.id}
              request={request}
              busy={busy === request.id}
              onAct={act}
            />
          ))}
        </ul>
      )}
    </div>
  );
}

function RequestCard({
  request,
  busy,
  onAct,
}: {
  request: StaffRentalRequest;
  busy: boolean;
  onAct: (request: StaffRentalRequest, route: string) => void;
}) {
  return (
    <li className="rounded-xl border border-border bg-surface p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone={STATUS_TONE[request.status]}>{request.status_label}</Badge>
            {/* Une demande sans compte ne se relance pas toute seule : si
                personne ne rappelle, elle est perdue. On le signale. */}
            {!request.has_account && <Badge tone="warning">Sans compte</Badge>}
          </div>

          <Link
            href={`/produits/${request.product.slug}`}
            target="_blank"
            className="mt-2 block font-semibold hover:underline"
          >
            {request.product.title} ↗
          </Link>
          <p className="text-sm text-foreground-muted">
            {request.product.city} ·{" "}
            {formatPrice(request.product.price, request.product.currency)}
          </p>

          <p className="mt-2 text-sm">
            <strong>
              {request.end_date
                ? `Du ${formatDay(request.start_date)} au ${formatDay(request.end_date)}`
                : `À partir du ${formatDay(request.start_date)}`}
            </strong>
            {request.end_date
              ? ` · ${request.nights} jour${(request.nights ?? 0) > 1 ? "s" : ""}`
              : " · durée indéterminée"}
          </p>

          <p className="mt-1 text-sm">
            {request.client_name} —{" "}
            <a href={`tel:${request.requester_phone}`} className="font-medium text-brand-700">
              {request.requester_phone}
            </a>
          </p>

          {request.message && (
            <p className="mt-2 whitespace-pre-line rounded-lg bg-surface-muted p-2 text-sm">
              {request.message}
            </p>
          )}
        </div>

        <div className="shrink-0 text-right text-xs text-foreground-muted">
          <p>Propriétaire : {request.supplier_name}</p>
          {request.supplier_checked_at && <p>Vérifié le {formatDay(request.supplier_checked_at)}</p>}
          {request.handled_by_name && <p>Suivi par {request.handled_by_name}</p>}
          {request.thread && (
            <Link
              href={`/compte/messages/${request.thread}`}
              className="mt-1 inline-block text-brand-700 underline underline-offset-2"
            >
              Ouvrir le fil
            </Link>
          )}
        </div>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        {request.status === "submitted" && (
          <Button size="sm" variant="secondary" disabled={busy} onClick={() => onAct(request, "checking")}>
            Je m&apos;en occupe
          </Button>
        )}
        {!request.contact_released && (
          <>
            <Button size="sm" disabled={busy} onClick={() => onAct(request, "available")}>
              Disponible
            </Button>
            <Button size="sm" variant="secondary" disabled={busy} onClick={() => onAct(request, "unavailable")}>
              Indisponible
            </Button>
          </>
        )}
        {request.supplier_checked_at && !request.contact_released && request.status !== "unavailable" && (
          <Button size="sm" disabled={busy} onClick={() => onAct(request, "release-contact")}>
            Transmettre les coordonnées
          </Button>
        )}
      </div>
    </li>
  );
}

function formatDay(iso: string) {
  return new Date(iso).toLocaleDateString("fr-FR", { day: "numeric", month: "short", year: "numeric" });
}
