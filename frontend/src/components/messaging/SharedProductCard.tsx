import Image from "next/image";
import Link from "next/link";
import { formatPrice } from "@/lib/format";
import type { ProductListItem } from "@/lib/types";

/**
 * L'annonce jointe a un message.
 *
 * Chaque ligne declare sa couleur. La carte est posee dans une bulle qui
 * peut etre indigo et imposer `text-white` : sans couleur explicite, le
 * titre heritait du blanc et disparaissait sur le fond clair de la carte.
 * Le prix et la ville, eux, etaient deja colores et restaient lisibles —
 * d'ou un titre invisible et deux lignes visibles, difficile a remarquer.
 */
export function SharedProductCard({ product }: { product: ProductListItem }) {
  return (
    <Link
      href={`/produits/${product.slug}`}
      className="mt-1 flex w-full min-w-0 items-center gap-3 rounded-lg border border-border bg-surface p-2 hover:border-brand-300 sm:w-64"
    >
      <div className="relative h-12 w-12 shrink-0 overflow-hidden rounded-md bg-surface-muted">
        {product.cover_image && <Image src={product.cover_image} alt="" fill className="object-cover" />}
      </div>
      <div className="min-w-0">
        <p className="truncate text-sm font-medium text-foreground">{product.title}</p>
        <p className="text-xs text-brand-700">{formatPrice(product.price, product.currency)}</p>
        <p className="truncate text-xs text-foreground-muted">{product.city}</p>
      </div>
    </Link>
  );
}
