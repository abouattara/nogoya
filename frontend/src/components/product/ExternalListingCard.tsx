import type { ProductDetail } from "@/lib/types";

/**
 * Le panneau qui remplace le contact NOGOYA sur une annonce référencée.
 *
 * Il dit trois choses, et c'est un choix : d'où vient l'annonce, quand on
 * l'a vue pour la dernière fois, et où aller pour la traiter. Il
 * n'affiche **pas** de bouton « Réserver » : NOGOYA ne peut pas garantir la
 * réservation d'un bien qu'elle ne gère pas, et un bouton qui promet ce
 * qu'on ne tient pas coûte plus cher qu'un bouton absent.
 */
export function ExternalListingCard({ product }: { product: ProductDetail }) {
  const sourceName = product.source?.name ?? "une source externe";
  const checked = product.last_checked_at
    ? new Date(product.last_checked_at).toLocaleDateString("fr-FR", {
        day: "numeric",
        month: "long",
        year: "numeric",
      })
    : null;

  return (
    <aside className="rounded-xl border border-border bg-surface p-5">
      <p className="inline-flex items-center rounded-full bg-surface-muted px-2.5 py-1 text-xs font-medium text-foreground-muted">
        Annonce référencée
      </p>

      <h2 className="mt-3 text-base font-semibold text-foreground">
        Publiée par {sourceName}
      </h2>
      <p className="mt-2 text-sm text-foreground-muted">
        Ce bien n&apos;est pas géré par NOGOYA. Les informations proviennent de la source
        et le contact se fait directement chez elle.
      </p>

      {checked && (
        <p className="mt-3 text-xs text-foreground-muted">
          Dernière vérification&nbsp;: {checked}
        </p>
      )}

      {product.source_url ? (
        <a
          href={product.source_url}
          target="_blank"
          // `noopener` et `nofollow` : le lien pointe vers un tiers dont on
          // ne répond pas, et on ne lui transmet pas notre référencement.
          rel="noopener noreferrer nofollow"
          className="mt-4 flex w-full items-center justify-center rounded-lg bg-brand-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-brand-700"
        >
          Voir l&apos;annonce originale
        </a>
      ) : (
        <p className="mt-4 rounded-lg bg-surface-muted px-3 py-2 text-sm text-foreground-muted">
          Le lien d&apos;origine n&apos;est pas disponible pour cette annonce.
        </p>
      )}

      {product.source?.reference_url && (
        <a
          href={product.source.reference_url}
          target="_blank"
          rel="noopener noreferrer nofollow"
          className="mt-2 block text-center text-xs text-foreground-muted underline underline-offset-2"
        >
          À propos de {sourceName}
        </a>
      )}
    </aside>
  );
}
