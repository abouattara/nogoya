"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import Image from "next/image";
import Link from "next/link";
import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Badge, EmptyState, ErrorState, Skeleton } from "@/components/ui/Feedback";
import { RequireAuth } from "@/components/providers/RequireAuth";
import { apiFetch, ApiError } from "@/lib/client-api";
import { formatPrice, rentalPeriodLabel } from "@/lib/format";
import type {
  ModerationDecision,
  ModerationProduct,
  Paginated,
  ProductStatus,
} from "@/lib/types";

/**
 * L'écran où une annonce est acceptée ou refusée.
 *
 * Les annonces des membres et celles importées depuis une source y passent
 * ensemble : la question posée est la même — ce bien mérite-t-il d'être
 * montré ? — et les séparer ferait oublier l'une des deux files.
 *
 * Trois partis pris :
 *
 * * **Toutes les photos, pas la couverture.** On refuse souvent sur la
 *   deuxième image. Les afficher en bande évite d'ouvrir chaque annonce.
 * * **Aucune coordonnée du vendeur.** Modérer ne demande pas de savoir qui
 *   joindre ; l'écran serait alors un annuaire.
 * * **Rien n'est masqué après décision.** La carte reste, avec son nouvel
 *   état : une erreur de clic doit pouvoir se rattraper tout de suite.
 */

const QUEUES: { key: string; label: string; statuses: ProductStatus[] }[] = [
  { key: "a-traiter", label: "À traiter", statuses: ["pending", "draft"] },
  { key: "publiees", label: "Publiées", statuses: ["approved"] },
  { key: "refusees", label: "Refusées", statuses: ["rejected"] },
  { key: "retirees", label: "Retirées", statuses: ["unavailable", "expired", "archived"] },
];

const STATUS_TONE: Record<ProductStatus, "warning" | "brand" | "danger" | "neutral"> = {
  draft: "warning",
  pending: "warning",
  approved: "brand",
  rejected: "danger",
  expired: "danger",
  unavailable: "danger",
  archived: "neutral",
};

const STATUS_LABEL: Record<ProductStatus, string> = {
  draft: "Brouillon",
  pending: "En attente",
  approved: "Publiée",
  rejected: "Refusée",
  expired: "Expirée",
  unavailable: "Indisponible",
  archived: "Archivée",
};

export default function ModerationPage() {
  return (
    <RequireAuth>
      {() => <ModerationQueue />}
    </RequireAuth>
  );
}

function ModerationQueue() {
  const queryClient = useQueryClient();
  const [queue, setQueue] = useState(QUEUES[0]);
  const [provenance, setProvenance] = useState("");
  const [search, setSearch] = useState("");
  const [pending, setPending] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const params = new URLSearchParams();
  queue.statuses.forEach((s) => params.append("status", s));
  if (provenance) params.set("provenance", provenance);
  if (search.trim()) params.set("search", search.trim());
  const query = params.toString();

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["moderation", query],
    queryFn: () => apiFetch<Paginated<ModerationProduct>>(`/api/v1/products/moderation/?${query}`),
    // Une file de modération se regarde à plusieurs : la garder fraîche
    // évite de décider deux fois sur la même annonce.
    staleTime: 10_000,
  });

  async function decide(product: ModerationProduct, action: ModerationDecision) {
    setPending(product.slug);
    setError(null);
    try {
      await apiFetch(`/api/v1/products/${product.slug}/moderate/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action }),
      });
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["moderation"] }),
        // Le catalogue public change aussi : ne pas l'invalider laisserait
        // le modérateur douter de ce qu'il vient de faire.
        queryClient.invalidateQueries({ queryKey: ["products"] }),
      ]);
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        setError("Votre compte n'a pas les droits de modération.");
      } else if (err instanceof ApiError) {
        setError(`La décision n'a pas pu être enregistrée (erreur ${err.status}).`);
      } else {
        setError("Connexion interrompue : la décision n'a pas été enregistrée.");
      }
    } finally {
      setPending(null);
    }
  }

  if (isError) {
    // Le serveur reste l'autorité : si l'API refuse, on le dit sans
    // prétendre deviner pourquoi depuis le navigateur.
    return (
      <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
        <ErrorState
          message="Impossible de charger la file de modération. Cet écran est réservé à l'équipe."
          retry={() => refetch()}
        />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Modération des annonces</h1>
          <p className="mt-1 text-sm text-foreground-muted">
            Annonces des membres et annonces importées, dans la même file.
          </p>
        </div>
        <Link href="/compte" className="text-sm text-brand-700 underline underline-offset-2">
          ← Mon compte
        </Link>
      </div>

      <div className="mb-4 flex flex-wrap gap-2" role="tablist" aria-label="Files de modération">
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

      <div className="mb-6 flex flex-wrap gap-2">
        <select
          value={provenance}
          onChange={(e) => setProvenance(e.target.value)}
          aria-label="Filtrer par origine"
          className="rounded-lg border border-border bg-surface px-3 py-2 text-sm"
        >
          <option value="">Toutes les origines</option>
          <option value="nogoya_owner">Membres NOGOYA</option>
          <option value="authorized_partner">Partenaires</option>
          <option value="external_reference">Annonces référencées</option>
        </select>
        <input
          type="search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Rechercher un titre…"
          aria-label="Rechercher une annonce"
          className="min-w-48 flex-1 rounded-lg border border-border bg-surface px-3 py-2 text-sm"
        />
      </div>

      {error && (
        <p role="alert" className="mb-4 text-sm text-danger-fg">
          {error}
        </p>
      )}

      {isLoading ? (
        <div className="flex flex-col gap-4">
          <Skeleton className="h-40 w-full" />
          <Skeleton className="h-40 w-full" />
        </div>
      ) : !data || data.results.length === 0 ? (
        <EmptyState
          title="Rien à traiter"
          description="Aucune annonce ne correspond à cette file."
        />
      ) : (
        <>
          <p className="mb-3 text-sm text-foreground-muted">
            {data.count} annonce{data.count > 1 ? "s" : ""}
          </p>
          <ul className="flex flex-col gap-4">
            {data.results.map((product) => (
              <ModerationCard
                key={product.id}
                product={product}
                busy={pending === product.slug}
                onDecide={decide}
              />
            ))}
          </ul>
        </>
      )}
    </div>
  );
}

function ModerationCard({
  product,
  busy,
  onDecide,
}: {
  product: ModerationProduct;
  busy: boolean;
  onDecide: (product: ModerationProduct, action: ModerationDecision) => void;
}) {
  const external = product.provenance !== "nogoya_owner";

  return (
    <li className="rounded-xl border border-border bg-surface p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone={STATUS_TONE[product.status]}>{STATUS_LABEL[product.status]}</Badge>
            {external && (
              <Badge tone="neutral">
                {product.source_name ?? "Source externe"}
              </Badge>
            )}
            <span className="text-xs text-foreground-muted">{product.category_name}</span>
          </div>
          <h2 className="mt-2 text-base font-semibold">{product.title}</h2>
          <p className="text-sm text-foreground-muted">
            {[product.location, product.city].filter(Boolean).join(", ")} ·{" "}
            {formatPrice(product.price, product.currency)}
            {product.listing_type === "rent" && ` / ${rentalPeriodLabel(product.rental_period)}`}
          </p>
          <p className="text-xs text-foreground-muted">Proposée par {product.supplier_name}</p>
        </div>

        <div className="flex shrink-0 flex-col items-end gap-1 text-xs">
          <Link
            href={`/produits/${product.slug}`}
            target="_blank"
            className="text-brand-700 underline underline-offset-2"
          >
            Voir la fiche ↗
          </Link>
          {external && product.source_url && (
            <a
              href={product.source_url}
              target="_blank"
              rel="noopener noreferrer nofollow"
              className="text-brand-700 underline underline-offset-2"
            >
              Annonce d&apos;origine ↗
            </a>
          )}
        </div>
      </div>

      {product.description && (
        <p className="mt-3 whitespace-pre-line text-sm text-foreground">{product.description}</p>
      )}

      {product.images.length > 0 ? (
        <div className="mt-3 flex flex-wrap gap-2">
          {product.images.map((image, index) => (
            <a
              key={image.id}
              href={image.image}
              target="_blank"
              rel="noopener noreferrer"
              className="relative h-24 w-24 overflow-hidden rounded-lg border border-border"
            >
              {/* Un vrai texte alternatif, pas `alt=""` : ici les photos
                  sont ce qu'on examine, pas une décoration. */}
              <Image
                src={image.image}
                alt={`Photo ${index + 1} de ${product.title}`}
                fill
                className="object-cover"
                unoptimized
              />
            </a>
          ))}
        </div>
      ) : (
        <p className="mt-3 text-sm text-foreground-muted">
          Aucune photo — une annonce sans image convertit mal.
        </p>
      )}

      <div className="mt-4 flex flex-wrap gap-2">
        {product.status !== "approved" && (
          <Button size="sm" disabled={busy} onClick={() => onDecide(product, "approve")}>
            Publier
          </Button>
        )}
        {product.status !== "rejected" && (
          <Button
            size="sm"
            variant="secondary"
            disabled={busy}
            onClick={() => onDecide(product, "reject")}
          >
            Refuser
          </Button>
        )}
        {product.status !== "unavailable" && (
          <Button
            size="sm"
            variant="secondary"
            disabled={busy}
            onClick={() => onDecide(product, "unavailable")}
          >
            Indisponible
          </Button>
        )}
        {product.status !== "archived" && (
          <Button
            size="sm"
            variant="secondary"
            disabled={busy}
            onClick={() => onDecide(product, "archive")}
          >
            Archiver
          </Button>
        )}
      </div>
    </li>
  );
}
