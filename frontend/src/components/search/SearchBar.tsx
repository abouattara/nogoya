"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useState, type FormEvent } from "react";

export function SearchBar({ compact = false }: { compact?: boolean }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [value, setValue] = useState(searchParams.get("search") ?? "");

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    const params = new URLSearchParams(searchParams.toString());
    if (value.trim()) params.set("search", value.trim());
    else params.delete("search");
    params.delete("page");
    router.push(`/produits?${params.toString()}`);
  }

  return (
    <form onSubmit={onSubmit} className="flex w-full max-w-xl items-center gap-2" role="search">
      <div className="relative flex-1">
        <svg
          className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-foreground-muted"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          aria-hidden="true"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-4.35-4.35M17 11a6 6 0 11-12 0 6 6 0 0112 0z" />
        </svg>
        <input
          type="search"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="Que cherchez-vous ? (véhicule, logement, matériel...)"
          aria-label="Rechercher un article"
          className={`w-full rounded-full border border-border bg-surface text-foreground pl-9 pr-4 text-sm outline-none focus:border-brand-600 focus:ring-1 focus:ring-brand-600 ${
            compact ? "py-1.5" : "py-2.5"
          }`}
        />
      </div>
      <button
        type="submit"
        className="rounded-full bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
      >
        Rechercher
      </button>
    </form>
  );
}
