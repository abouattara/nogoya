import Image from "next/image";
import Link from "next/link";
import { formatPrice } from "@/lib/format";
import type { ProductListItem } from "@/lib/types";

export function SharedProductCard({ product }: { product: ProductListItem }) {
  return (
    <Link
      href={`/produits/${product.slug}`}
      className="mt-1 flex w-64 items-center gap-3 rounded-lg border border-border bg-surface p-2 hover:border-brand-300"
    >
      <div className="relative h-12 w-12 shrink-0 overflow-hidden rounded-md bg-surface-muted">
        {product.cover_image && <Image src={product.cover_image} alt="" fill className="object-cover" />}
      </div>
      <div className="min-w-0">
        <p className="truncate text-sm font-medium">{product.title}</p>
        <p className="text-xs text-brand-700">{formatPrice(product.price, product.currency)}</p>
        <p className="truncate text-xs text-foreground-muted">{product.city}</p>
      </div>
    </Link>
  );
}
