"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter, useSearchParams } from "next/navigation";
import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { Input, Select } from "@/components/ui/Input";
import { apiFetch } from "@/lib/client-api";
import type { Category } from "@/lib/types";

function flattenCategories(categories: Category[], depth = 0): Array<{ id: number; slug: string; name: string; depth: number }> {
  return categories.flatMap((cat) => [
    { id: cat.id, slug: cat.slug, name: cat.name, depth },
    ...flattenCategories(cat.children, depth + 1),
  ]);
}

export function SupplierCatalogControls({ basePath }: { basePath: string }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [search, setSearch] = useState(searchParams.get("search") ?? "");
  const [priceMin, setPriceMin] = useState(searchParams.get("price_min") ?? "");
  const [priceMax, setPriceMax] = useState(searchParams.get("price_max") ?? "");
  const [category, setCategory] = useState(searchParams.get("category") ?? "");

  const { data: categories } = useQuery({
    queryKey: ["categories"],
    queryFn: () => apiFetch<Category[]>("/api/v1/categories/", { auth: false }),
  });
  const flatCategories = categories ? flattenCategories(categories) : [];

  function apply(e: FormEvent) {
    e.preventDefault();
    const params = new URLSearchParams(searchParams.toString());
    const set = (key: string, value: string) => (value ? params.set(key, value) : params.delete(key));
    set("search", search);
    set("price_min", priceMin);
    set("price_max", priceMax);
    set("category", category);
    params.delete("page");
    router.push(`${basePath}?${params.toString()}`);
  }

  function setOrdering(value: string) {
    const params = new URLSearchParams(searchParams.toString());
    if (value) params.set("ordering", value);
    else params.delete("ordering");
    params.delete("page");
    router.push(`${basePath}?${params.toString()}`);
  }

  return (
    <form onSubmit={apply} className="flex flex-wrap items-end gap-3 rounded-xl border border-border bg-surface-muted p-4">
      <div className="min-w-[180px] flex-1">
        <Input label="Rechercher dans ce catalogue" value={search} onChange={(e) => setSearch(e.target.value)} />
      </div>
      <div className="w-44">
        <Select label="Catégorie" value={category} onChange={(e) => setCategory(e.target.value)}>
          <option value="">Toutes</option>
          {flatCategories.map((cat) => (
            <option key={cat.id} value={cat.slug}>
              {"  ".repeat(cat.depth)}
              {cat.name}
            </option>
          ))}
        </Select>
      </div>
      <div className="w-28">
        <Input label="Prix min" inputMode="numeric" value={priceMin} onChange={(e) => setPriceMin(e.target.value)} />
      </div>
      <div className="w-28">
        <Input label="Prix max" inputMode="numeric" value={priceMax} onChange={(e) => setPriceMax(e.target.value)} />
      </div>
      <div className="w-44">
        <Select label="Trier par" defaultValue={searchParams.get("ordering") ?? "-created_at"} onChange={(e) => setOrdering(e.target.value)}>
          <option value="-created_at">Plus récent</option>
          <option value="price">Prix croissant</option>
          <option value="-price">Prix décroissant</option>
          <option value="-views_count">Popularité</option>
        </Select>
      </div>
      <Button type="submit" variant="secondary">
        Filtrer
      </Button>
    </form>
  );
}
