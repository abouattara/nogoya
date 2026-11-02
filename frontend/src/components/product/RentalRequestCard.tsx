"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { apiFetch, ApiError } from "@/lib/client-api";
import { useAuthStore } from "@/store/auth-store";
import type { RentalRequest } from "@/lib/types";

/**
 * Le panneau qui remplace le contact direct du fournisseur.
 *
 * Le client ne voit plus de numéro de téléphone : il dit ce qu'il veut et
 * pour quelles dates, et NOGOYA vérifie la disponibilité auprès du
 * fournisseur avant toute mise en relation. C'est tout l'intérêt du
 * schéma — promettre un bien sans avoir vérifié qu'il est libre est la
 * seule faute qu'il existe pour éviter.
 *
 * Les dates ne sont pas un ornement : sans elles, « est-ce disponible ? »
 * n'a pas de réponse. Un logement libre en mars ne l'est pas en avril.
 */
export function RentalRequestCard({
  slug,
  productId,
  productTitle,
}: {
  slug: string;
  productId: number;
  productTitle: string;
}) {
  const user = useAuthStore((state) => state.user);
  const router = useRouter();

  const today = new Date().toISOString().slice(0, 10);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [message, setMessage] = useState("");
  const [sending, setSending] = useState(false);
  const [submitted, setSubmitted] = useState<RentalRequest | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);

    if (!startDate || !endDate) {
      setError("Indiquez les dates souhaitées.");
      return;
    }
    if (endDate < startDate) {
      setError("La date de fin ne peut pas précéder la date de début.");
      return;
    }

    setSending(true);
    try {
      const created = await apiFetch<RentalRequest>("/api/v1/rental-requests/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          product: productId,
          start_date: startDate,
          end_date: endDate,
          message,
        }),
      });
      setSubmitted(created);
    } catch (err) {
      if (err instanceof ApiError) {
        const body = err.body as Record<string, unknown> | null;
        const detail = body
          ? Object.values(body)
              .flat()
              .map((m) => String(m))
              .join(" ")
          : "";
        setError(detail || `La demande n'a pas pu être envoyée (erreur ${err.status}).`);
      } else {
        setError("Connexion interrompue : la demande n'a pas été envoyée.");
      }
    } finally {
      setSending(false);
    }
  }

  if (!user) {
    return (
      <aside className="rounded-xl border border-border bg-surface p-5">
        <h2 className="text-base font-semibold">Ce bien vous intéresse&nbsp;?</h2>
        <p className="mt-2 text-sm text-foreground-muted">
          Connectez-vous pour faire une demande. Nous vérifions la disponibilité auprès du
          propriétaire avant de vous mettre en relation.
        </p>
        <Link
          href={`/login?next=/produits/${slug}`}
          className="mt-4 flex w-full items-center justify-center rounded-lg bg-brand-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-brand-700"
        >
          Se connecter
        </Link>
      </aside>
    );
  }

  if (submitted) {
    return (
      <aside className="rounded-xl border border-brand-200 bg-brand-50 p-5">
        <h2 className="text-base font-semibold text-brand-900">Demande envoyée</h2>
        <p className="mt-2 text-sm text-brand-900/80">
          Nous contactons le propriétaire pour confirmer la disponibilité du{" "}
          <strong>{formatDay(submitted.start_date)}</strong> au{" "}
          <strong>{formatDay(submitted.end_date)}</strong>, puis nous revenons vers vous.
        </p>
        <div className="mt-4 flex flex-col gap-2">
          {submitted.thread && (
            <Link
              href={`/compte/messages/${submitted.thread}`}
              className="flex w-full items-center justify-center rounded-lg bg-brand-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-brand-700"
            >
              Suivre ma demande
            </Link>
          )}
          <Link
            href="/compte/demandes"
            className="text-center text-sm text-brand-800 underline underline-offset-2"
          >
            Toutes mes demandes
          </Link>
        </div>
      </aside>
    );
  }

  return (
    <aside className="rounded-xl border border-border bg-surface p-5">
      <h2 className="text-base font-semibold">Demander ce bien</h2>
      <p className="mt-1 text-sm text-foreground-muted">
        Nous vérifions la disponibilité auprès du propriétaire, puis nous vous mettons en
        relation.
      </p>

      <form onSubmit={submit} className="mt-4 flex flex-col gap-3">
        <div className="grid grid-cols-2 gap-2">
          <Input
            label="Du"
            type="date"
            min={today}
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
          />
          <Input
            label="Au"
            type="date"
            min={startDate || today}
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
          />
        </div>

        <label className="flex flex-col gap-1">
          <span className="text-sm font-medium">Votre message (facultatif)</span>
          <textarea
            rows={3}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder={`Une question sur « ${productTitle} » ?`}
            className="rounded-lg border border-border bg-surface px-3 py-2 text-sm text-foreground placeholder:text-foreground-muted focus-visible:outline-2 focus-visible:outline-brand-600"
          />
        </label>

        {error && (
          <p role="alert" className="text-sm text-danger-fg">
            {error}
          </p>
        )}

        <Button type="submit" disabled={sending}>
          {sending ? "Envoi…" : "Envoyer ma demande"}
        </Button>
      </form>

      <p className="mt-3 text-xs text-foreground-muted">
        Les coordonnées du propriétaire vous sont transmises par NOGOYA une fois la
        disponibilité confirmée.
      </p>

      <button
        type="button"
        onClick={() => router.push(`/compte/messages?produit=${productId}`)}
        className="mt-3 w-full text-center text-sm text-brand-700 underline underline-offset-2"
      >
        Poser une question sans réserver
      </button>
    </aside>
  );
}

function formatDay(iso: string) {
  return new Date(iso).toLocaleDateString("fr-FR", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}
