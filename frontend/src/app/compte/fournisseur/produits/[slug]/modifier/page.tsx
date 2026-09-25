"use client";

import { useQuery } from "@tanstack/react-query";
import { use } from "react";
import { ErrorState, Skeleton } from "@/components/ui/Feedback";
import { ProductForm } from "@/components/product/ProductForm";
import { RequireAuth } from "@/components/providers/RequireAuth";
import { apiFetch } from "@/lib/client-api";
import type { ProductDetail } from "@/lib/types";

export default function EditProductPage({ params }: PageProps<"/compte/fournisseur/produits/[slug]/modifier">) {
  const { slug } = use(params);

  return (
    <RequireAuth role="supplier">
      {() => (
        <div className="mx-auto max-w-2xl px-4 py-8 sm:px-6">
          <h1 className="mb-6 text-2xl font-bold">Modifier l&apos;annonce</h1>
          <EditForm slug={slug} />
        </div>
      )}
    </RequireAuth>
  );
}

function EditForm({ slug }: { slug: string }) {
  const { data: product, isLoading, isError, refetch } = useQuery({
    queryKey: ["product", slug],
    queryFn: () => apiFetch<ProductDetail>(`/api/v1/products/${slug}/`),
  });

  if (isLoading) return <Skeleton className="h-96 w-full" />;
  if (isError || !product) {
    return <ErrorState message="Impossible de charger cette annonce (elle n'existe peut-être pas, ou ne vous appartient pas)." retry={refetch} />;
  }

  return <ProductForm mode="edit" product={product} />;
}
