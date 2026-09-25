"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import clsx from "clsx";
import { apiFetch } from "@/lib/client-api";
import { useFavoriteSlugs, useInvalidateFavorites } from "./use-favorite-slugs";
import { useAuthStore } from "@/store/auth-store";

interface FavoriteButtonProps {
  slug: string;
  initial: boolean;
  /** "icon" overlays a product card, "button" sits on the detail page. */
  variant?: "icon" | "button";
  className?: string;
}

export function FavoriteButton({ slug, initial, variant = "icon", className }: FavoriteButtonProps) {
  const user = useAuthStore((s) => s.user);
  const router = useRouter();
  const invalidateFavorites = useInvalidateFavorites();
  const favoriteSlugs = useFavoriteSlugs();
  // `initial` comes from the anonymous SSR fetch, so it is always false for a
  // signed-in visitor. Order: what this button just did > what the browser
  // knows about this user > the server-rendered guess.
  const [override, setOverride] = useState<boolean | null>(null);
  const isFavorite = override ?? favoriteSlugs?.has(slug) ?? initial;
  const [pending, setPending] = useState(false);

  async function toggle(event: React.MouseEvent) {
    // Cards wrap this button in a <Link>; don't navigate when favouriting.
    event.preventDefault();
    event.stopPropagation();

    if (!user) {
      router.push("/login");
      return;
    }

    const next = !isFavorite;
    setOverride(next); // optimistic
    setPending(true);
    try {
      const result = await apiFetch<{ is_favorite: boolean }>(
        `/api/v1/products/${slug}/toggle_favorite/`,
        { method: "POST" }
      );
      setOverride(result.is_favorite);
      invalidateFavorites();
    } catch {
      setOverride(!next); // roll back
    } finally {
      setPending(false);
    }
  }

  const label = isFavorite ? "Retirer des favoris" : "Ajouter aux favoris";

  if (variant === "button") {
    return (
      <button
        onClick={toggle}
        disabled={pending}
        aria-pressed={isFavorite}
        aria-label={label}
        className={clsx(
          "inline-flex items-center justify-center gap-2 rounded-lg border px-4 py-2 text-sm font-medium transition-colors",
          isFavorite
            ? "border-brand-300 bg-brand-50 text-brand-800 hover:bg-brand-100"
            : "border-border bg-surface text-foreground hover:bg-surface-muted",
          className
        )}
      >
        <HeartIcon filled={isFavorite} />
        {isFavorite ? "Dans vos favoris" : "Ajouter aux favoris"}
      </button>
    );
  }

  return (
    <button
      onClick={toggle}
      disabled={pending}
      aria-pressed={isFavorite}
      aria-label={label}
      title={label}
      className={clsx(
        "flex h-8 w-8 items-center justify-center rounded-full bg-surface/90 text-brand-700 shadow-sm backdrop-blur transition-colors hover:bg-surface",
        className
      )}
    >
      <HeartIcon filled={isFavorite} />
    </button>
  );
}

function HeartIcon({ filled }: { filled: boolean }) {
  return (
    <svg
      className="h-4 w-4"
      viewBox="0 0 24 24"
      fill={filled ? "currentColor" : "none"}
      stroke="currentColor"
      strokeWidth={2}
      aria-hidden="true"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"
      />
    </svg>
  );
}
