"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState, type FormEvent } from "react";
import clsx from "clsx";
import { Button } from "@/components/ui/Button";
import { Input, Select } from "@/components/ui/Input";
import type { Category } from "@/lib/types";

function withParam(searchParams: URLSearchParams, key: string, value?: string) {
  const params = new URLSearchParams(searchParams.toString());
  if (value) params.set(key, value);
  else params.delete(key);
  params.delete("page");
  return params.toString();
}

/** Attributes of the selected category that are flagged `filterable`. */
function findFilterableAttributes(categories: Category[], slug: string | null) {
  if (!slug) return [];
  function walk(list: Category[]): Category | undefined {
    for (const category of list) {
      if (category.slug === slug) return category;
      const nested = walk(category.children);
      if (nested) return nested;
    }
    return undefined;
  }
  return (walk(categories)?.attributes ?? []).filter((attribute) => attribute.filterable);
}

export function FiltersSidebar({ categories }: { categories: Category[] }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const activeCategory = searchParams.get("category");
  const activeListingType = searchParams.get("listing_type");

  const [city, setCity] = useState(searchParams.get("city") ?? "");
  const [priceMin, setPriceMin] = useState(searchParams.get("price_min") ?? "");
  const [priceMax, setPriceMax] = useState(searchParams.get("price_max") ?? "");

  const attributeFilters = findFilterableAttributes(categories, activeCategory);

  function applyText(e: FormEvent) {
    e.preventDefault();
    let params = new URLSearchParams(searchParams.toString());
    params = new URLSearchParams(withParam(params, "city", city));
    params = new URLSearchParams(withParam(params, "price_min", priceMin));
    params = new URLSearchParams(withParam(params, "price_max", priceMax));
    router.push(`/produits?${params.toString()}`);
  }

  function setAttributeFilter(key: string, value: string) {
    router.push(`/produits?${withParam(searchParams, key, value)}`);
  }

  return (
    <aside className="flex w-full flex-col gap-6 lg:w-64 lg:shrink-0">
      <div>
        <h3 className="mb-2 text-sm font-semibold">Catégories</h3>
        <ul className="flex flex-col gap-1">
          <FilterLink
            label="Toutes les catégories"
            active={!activeCategory}
            href={`/produits?${withParam(searchParams, "category")}`}
          />
          {categories.map((cat) => (
            <li key={cat.id}>
              <FilterLink
                label={cat.name}
                active={activeCategory === cat.slug}
                href={`/produits?${withParam(searchParams, "category", cat.slug)}`}
              />
              {cat.children.length > 0 && (
                <ul className="ml-3 mt-1 flex flex-col gap-1 border-l border-border pl-2">
                  {cat.children.map((child) => (
                    <li key={child.id}>
                      <FilterLink
                        label={child.name}
                        active={activeCategory === child.slug}
                        href={`/produits?${withParam(searchParams, "category", child.slug)}`}
                      />
                    </li>
                  ))}
                </ul>
              )}
            </li>
          ))}
        </ul>
      </div>

      <div>
        <h3 className="mb-2 text-sm font-semibold">Type d&apos;offre</h3>
        <ul className="flex flex-col gap-1">
          <FilterLink label="Tous" active={!activeListingType} href={`/produits?${withParam(searchParams, "listing_type")}`} />
          <FilterLink
            label="Location"
            active={activeListingType === "rent"}
            href={`/produits?${withParam(searchParams, "listing_type", "rent")}`}
          />
          <FilterLink
            label="Vente"
            active={activeListingType === "sale"}
            href={`/produits?${withParam(searchParams, "listing_type", "sale")}`}
          />
        </ul>
      </div>

      <form onSubmit={applyText} className="flex flex-col gap-3">
        <h3 className="text-sm font-semibold">Ville</h3>
        <Input placeholder="Ouagadougou, Bobo..." value={city} onChange={(e) => setCity(e.target.value)} />

        <h3 className="text-sm font-semibold">Prix</h3>
        <div className="flex gap-2">
          <Input placeholder="Min" inputMode="numeric" value={priceMin} onChange={(e) => setPriceMin(e.target.value)} />
          <Input placeholder="Max" inputMode="numeric" value={priceMax} onChange={(e) => setPriceMax(e.target.value)} />
        </div>
        <Button type="submit" variant="secondary" size="sm">
          Appliquer
        </Button>
      </form>

      {attributeFilters.length > 0 && (
        <div className="flex flex-col gap-3">
          <h3 className="text-sm font-semibold">Caractéristiques</h3>
          {attributeFilters.map((attribute) => {
            const key = `attr_${attribute.slug}`;
            const current = searchParams.get(key) ?? "";

            if (attribute.attribute_type === "select" || attribute.attribute_type === "multi_select") {
              return (
                <Select
                  key={attribute.slug}
                  label={attribute.name}
                  value={current}
                  onChange={(e) => setAttributeFilter(key, e.target.value)}
                >
                  <option value="">Tous</option>
                  {attribute.options.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </Select>
              );
            }

            if (attribute.attribute_type === "boolean") {
              return (
                <Select
                  key={attribute.slug}
                  label={attribute.name}
                  value={current}
                  onChange={(e) => setAttributeFilter(key, e.target.value)}
                >
                  <option value="">Peu importe</option>
                  <option value="true">Oui</option>
                  <option value="false">Non</option>
                </Select>
              );
            }

            if (attribute.attribute_type === "number") {
              return (
                <NumberRangeFilter
                  key={attribute.slug}
                  label={attribute.unit ? `${attribute.name} (${attribute.unit})` : attribute.name}
                  minValue={searchParams.get(`${key}_min`) ?? ""}
                  maxValue={searchParams.get(`${key}_max`) ?? ""}
                  onApply={(min, max) => {
                    let params = new URLSearchParams(searchParams.toString());
                    params = new URLSearchParams(withParam(params, `${key}_min`, min));
                    params = new URLSearchParams(withParam(params, `${key}_max`, max));
                    router.push(`/produits?${params.toString()}`);
                  }}
                />
              );
            }

            return null;
          })}
        </div>
      )}
    </aside>
  );
}

function NumberRangeFilter({
  label,
  minValue,
  maxValue,
  onApply,
}: {
  label: string;
  minValue: string;
  maxValue: string;
  onApply: (min: string, max: string) => void;
}) {
  const [min, setMin] = useState(minValue);
  const [max, setMax] = useState(maxValue);

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        onApply(min, max);
      }}
      className="flex flex-col gap-2"
    >
      <span className="text-xs font-medium text-foreground-muted">{label}</span>
      <div className="flex gap-2">
        <Input placeholder="Min" inputMode="numeric" value={min} onChange={(e) => setMin(e.target.value)} />
        <Input placeholder="Max" inputMode="numeric" value={max} onChange={(e) => setMax(e.target.value)} />
      </div>
      <Button type="submit" variant="secondary" size="sm">
        Filtrer
      </Button>
    </form>
  );
}

function FilterLink({ label, active, href }: { label: string; active: boolean; href: string }) {
  return (
    <Link
      href={href}
      className={clsx(
        "block rounded-lg px-2 py-1.5 text-sm transition-colors",
        active ? "bg-brand-100 font-medium text-brand-dark" : "hover:bg-surface-muted"
      )}
    >
      {label}
    </Link>
  );
}
