"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { apiFetch } from "@/lib/client-api";

interface PendingSummary {
  pending: number;
  without_account: number;
}

/**
 * Le rappel des demandes en attente, posé là où l'équipe regarde déjà.
 *
 * Une demande venue d'un visiteur sans compte n'a pas de fil : elle
 * n'apparaît dans aucune conversation. L'équipe ouvrait donc sa messagerie,
 * n'y voyait rien, et la demande dormait — alors que personne ne relancera
 * à la place d'un visiteur anonyme.
 *
 * Plutôt que d'espérer qu'on pense à ouvrir un troisième écran, le compteur
 * vient à la messagerie et à la modération. Il disparaît quand la file est
 * vide : un bandeau permanent cesse vite d'être lu.
 */
export function PendingRequestsBanner() {
  const { data } = useQuery({
    queryKey: ["rental-requests-pending"],
    queryFn: () => apiFetch<PendingSummary>("/api/v1/rental-requests/pending-summary/"),
    // L'équipe n'est pas seule devant l'écran : on rafraîchit sans
    // l'obliger à recharger.
    refetchInterval: 60_000,
    // Un compte sans droits reçoit un 403 : on n'affiche rien, sans bruit.
    retry: false,
  });

  if (!data || data.pending === 0) return null;

  return (
    <Link
      href="/compte/demandes-recues"
      className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-brand-200 bg-brand-50 px-4 py-3 hover:border-brand-300"
    >
      <span className="text-sm text-brand-900">
        <strong>
          {data.pending} demande{data.pending > 1 ? "s" : ""} de location
        </strong>{" "}
        {data.pending > 1 ? "attendent" : "attend"} une vérification
        {data.without_account > 0 && (
          <>
            {" — dont "}
            <strong>
              {data.without_account} sans compte
            </strong>
            {", à rappeler par téléphone"}
          </>
        )}
        .
      </span>
      <span className="text-sm font-semibold text-brand-800 underline underline-offset-2">
        Ouvrir la file →
      </span>
    </Link>
  );
}
