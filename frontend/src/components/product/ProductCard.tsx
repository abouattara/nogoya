import Image from "next/image";
import Link from "next/link";
import { Badge } from "@/components/ui/Feedback";
import { FavoriteButton } from "@/components/product/FavoriteButton";
import type { ProductListItem } from "@/lib/types";
import { formatPrice, rentalPeriodLabel } from "@/lib/format";

export function ProductCard({ product }: { product: ProductListItem }) {
  return (
    <Link
      href={`/produits/${product.slug}`}
      className="group flex flex-col overflow-hidden rounded-xl border border-border transition-shadow hover:shadow-md"
    >
      <div className="relative aspect-4/3 w-full bg-surface-muted">
        {product.cover_image ? (
          <Image
            src={product.cover_image}
            alt={product.title}
            fill
            sizes="(max-width: 640px) 50vw, (max-width: 1024px) 33vw, 25vw"
            className="object-cover transition-transform group-hover:scale-105"
          />
        ) : (
          <div className="flex h-full items-center justify-center text-foreground-muted">Pas de photo</div>
        )}
        <div className="absolute left-2 top-2">
          <Badge tone={product.listing_type === "rent" ? "brand" : "warning"}>
            {product.listing_type === "rent" ? "Location" : "Vente"}
          </Badge>
        </div>
        <div className="absolute right-2 top-2">
          <FavoriteButton slug={product.slug} initial={product.is_favorite} />
        </div>
      </div>
      <div className="flex flex-1 flex-col gap-1 p-3">
        <p className="line-clamp-1 text-sm font-medium">{product.title}</p>
        <p className="text-xs text-foreground-muted">{product.city}</p>
        <div className="mt-auto flex items-center justify-between pt-1">
          <p className="text-sm font-semibold text-brand-dark">
            {formatPrice(product.price, product.currency)}
            {product.listing_type === "rent" && (
              <span className="font-normal text-foreground-muted"> / {rentalPeriodLabel(product.rental_period)}</span>
            )}
          </p>
          <span className="flex items-center gap-1 text-xs text-foreground-muted">
            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            {product.views_count}
          </span>
        </div>
      </div>
    </Link>
  );
}
