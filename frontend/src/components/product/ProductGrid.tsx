import { EmptyState } from "@/components/ui/Feedback";
import type { ProductListItem } from "@/lib/types";
import { ProductCard } from "./ProductCard";

export function ProductGrid({ products, emptyMessage }: { products: ProductListItem[]; emptyMessage?: string }) {
  if (products.length === 0) {
    return (
      <EmptyState
        title="Aucun article trouvé"
        description={emptyMessage ?? "Essayez d'élargir votre recherche ou vos filtres."}
      />
    );
  }

  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
      {products.map((product) => (
        <ProductCard key={product.id} product={product} />
      ))}
    </div>
  );
}
