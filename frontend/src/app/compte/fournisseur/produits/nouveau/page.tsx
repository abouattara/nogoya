"use client";

import { RequireAuth } from "@/components/providers/RequireAuth";
import { ProductForm } from "@/components/product/ProductForm";

export default function NewProductPage() {
  return (
    <RequireAuth role="supplier">
      {() => (
        <div className="mx-auto max-w-2xl px-4 py-8 sm:px-6">
          <h1 className="mb-6 text-2xl font-bold">Publier une annonce</h1>
          <ProductForm mode="create" />
        </div>
      )}
    </RequireAuth>
  );
}
