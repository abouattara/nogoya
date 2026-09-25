"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/client-api";
import { useAuthStore } from "@/store/auth-store";

const FAVORITE_SLUGS_KEY = ["favorite-slugs"] as const;

/**
 * The slugs this user has favourited.
 *
 * Product pages and cards are server-rendered and that fetch is anonymous,
 * so `is_favorite` is always `false` in the initial HTML. Without this, a
 * listing you had already saved showed an empty heart — and clicking it
 * quietly *removed* the favourite instead of adding one.
 *
 * Returns `null` while unknown (signed out, or still loading) so callers can
 * fall back to the server-rendered value rather than flashing "not saved".
 */
export function useFavoriteSlugs(): Set<string> | null {
  const user = useAuthStore((s) => s.user);
  const { data } = useQuery({
    queryKey: FAVORITE_SLUGS_KEY,
    queryFn: async () => {
      const payload = await apiFetch<{ slugs: string[] }>("/api/v1/favorites/slugs/");
      return payload.slugs;
    },
    enabled: Boolean(user),
    staleTime: 60_000,
  });

  if (!user || !data) return null;
  return new Set(data);
}

/** Keeps every heart on screen in sync after a toggle. */
export function useInvalidateFavorites() {
  const queryClient = useQueryClient();
  return () => {
    queryClient.invalidateQueries({ queryKey: FAVORITE_SLUGS_KEY });
    queryClient.invalidateQueries({ queryKey: ["favorites"] });
  };
}
