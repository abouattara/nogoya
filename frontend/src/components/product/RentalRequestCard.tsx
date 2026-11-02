"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { apiFetch, ApiError } from "@/lib/client-api";
import { useAuthStore } from "@/store/auth-store";
import type { RentalRequest } from "@/lib/types";

/**
 * Le panneau qui remplace le contact direct du fournisseur.
 *
 * Trois partis pris, chacun payé par un constat :
 *
 * * **Pas de compte obligatoire.** Exiger une inscription avant la première
 *   question fait fuir une part des clients, et le schéma intermédié ne
 *   l'impose pas : c'est NOGOYA qui rappelle, et un numéro suffit. Un
 *   visiteur identifié garde l'avantage de suivre sa demande et d'échanger
 *   dans un fil ; on le lui dit, on ne le lui impose pas.
 * * **La durée peut être inconnue.** Demander une date de fin pour une
 *   maison n'a pas de sens : on ne sait pas quand on la rendra. La case
 *   « durée indéterminée » remplace alors la seconde date.
 * * **Aucun numéro affiché.** NOGOYA vérifie la disponibilité auprès du
 *   propriétaire avant toute mise en relation.
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

  const today = new Date().toISOString().slice(0, 10);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [openEnded, setOpenEnded] = useState(false);
  const [message, setMessage] = useState("");
  const [guestName, setGuestName] = useState("");
  const [guestPhone, setGuestPhone] = useState("");
  const [sending, setSending] = useState(false);
  const [submitted, setSubmitted] = useState<RentalRequest | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);

    if (!startDate) {
      setError("Indiquez la date de début souhaitée.");
      return;
    }
    if (!openEnded && !endDate) {
      setError("Indiquez une date de fin, ou cochez « je ne sais pas encore ».");
      return;
    }
    if (!openEnded && endDate < startDate) {
      setError("La date de fin ne peut pas précéder la date de début.");
      return;
    }
    if (!user && !guestPhone.trim()) {
      setError("Laissez un numéro pour que nous puissions vous rappeler.");
      return;
    }

    setSending(true);
    try {
      const created = await apiFetch<RentalRequest>("/api/v1/rental-requests/", {
        method: "POST",
        // Sans compte, pas de jeton à joindre : la route l'accepte.
        auth: Boolean(user),
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          product: productId,
          start_date: startDate,
          end_date: openEnded ? null : endDate,
          open_ended: openEnded,
          message,
          ...(user ? {} : { guest_name: guestName, guest_phone: guestPhone }),
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

  if (submitted) {
    return (
      <aside className="rounded-xl border border-brand-200 bg-brand-50 p-5">
        <h2 className="text-base font-semibold text-brand-900">Demande envoyée</h2>
        <p className="mt-2 text-sm text-brand-900/80">
          Nous contactons le propriétaire pour confirmer la disponibilité{" "}
          {submitted.open_ended || !submitted.end_date ? (
            <>
              à partir du <strong>{formatDay(submitted.start_date)}</strong>
            </>
          ) : (
            <>
              du <strong>{formatDay(submitted.start_date)}</strong> au{" "}
              <strong>{formatDay(submitted.end_date)}</strong>
            </>
          )}
          , puis nous revenons vers vous.
        </p>

        {submitted.thread ? (
          <div className="mt-4 flex flex-col gap-2">
            <Link
              href={`/compte/messages/${submitted.thread}`}
              className="flex w-full items-center justify-center rounded-lg bg-brand-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-brand-700"
            >
              Suivre ma demande
            </Link>
            <Link
              href="/compte/demandes"
              className="text-center text-sm text-brand-800 underline underline-offset-2"
            >
              Toutes mes demandes
            </Link>
          </div>
        ) : (
          <p className="mt-3 text-sm text-brand-900/80">
            Nous vous rappelons au <strong>{guestPhone}</strong>.{" "}
            <Link
              href={`/register?next=/produits/${slug}`}
              className="underline underline-offset-2"
            >
              Créez un compte
            </Link>{" "}
            pour suivre vos demandes et échanger avec nous par écrit.
          </p>
        )}
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
        <div className={openEnded ? "" : "grid grid-cols-2 gap-2"}>
          <Input
            label="À partir du"
            type="date"
            min={today}
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
          />
          {!openEnded && (
            <Input
              label="Jusqu'au"
              type="date"
              min={startDate || today}
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
            />
          )}
        </div>

        <label className="flex items-start gap-2 text-sm">
          <input
            type="checkbox"
            checked={openEnded}
            onChange={(e) => setOpenEnded(e.target.checked)}
            className="mt-0.5"
          />
          <span>
            Je ne sais pas encore jusqu&apos;à quand
            <span className="block text-xs text-foreground-muted">
              Pour un logement ou une location de longue durée.
            </span>
          </span>
        </label>

        {!user && (
          <>
            <Input
              label="Votre nom"
              value={guestName}
              onChange={(e) => setGuestName(e.target.value)}
              placeholder="Awa Traoré"
            />
            <Input
              label="Votre téléphone"
              type="tel"
              inputMode="tel"
              value={guestPhone}
              onChange={(e) => setGuestPhone(e.target.value)}
              placeholder="70 00 00 00"
            />
          </>
        )}

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
        {user
          ? "Les coordonnées du propriétaire vous sont transmises par NOGOYA une fois la disponibilité confirmée."
          : "Pas besoin de compte. Nous vous rappelons au numéro indiqué une fois la disponibilité confirmée."}
      </p>
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
