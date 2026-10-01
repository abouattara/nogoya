"use client";

import { useAuthStore } from "@/store/auth-store";
import { VISITOR_HEADER, readVisitorCookie } from "@/lib/visitor";
import { UPLOAD_BOUNDARY_HEADER, UPLOAD_CONTENT_TYPE, encodeFormData } from "@/lib/multipart";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export class ApiError extends Error {
  status: number;
  body: unknown;
  constructor(status: number, body: unknown) {
    super(`API error ${status}`);
    this.status = status;
    this.body = body;
  }
}

let refreshInFlight: Promise<string | null> | null = null;

/**
 * Downloads a protected file (voice messages) with the same auth and
 * refresh handling as any other call.
 *
 * A bare `<audio src="/api/...">` cannot be used: the browser issues that
 * request without the Authorization header — the access token only lives in
 * memory — so the API answered 401 and the player showed "Vocal
 * indisponible".
 */
export async function apiFetchBlob(path: string): Promise<Blob> {
  // Not `application/json`, which apiFetch sends by default: DRF negotiates
  // the renderer from this header before the view runs.
  return apiFetch<Blob>(path, { parse: "blob", headers: { Accept: "*/*" } });
}

/**
 * Exchanges the httpOnly refresh cookie for a new access token.
 *
 * Every caller in the app (auth bootstrap on page load, 401 retries from
 * several widgets firing at once) MUST go through this single function:
 * SimpleJWT rotates and blacklists the refresh token on each use, so two
 * concurrent refreshes would make the second one fail and log the user out
 * mid-session. The in-flight promise is shared so that never happens.
 */
export async function refreshAccessToken(): Promise<string | null> {
  if (!refreshInFlight) {
    refreshInFlight = (async () => {
      try {
        const res = await fetch("/api/auth/refresh", { method: "POST" });
        if (!res.ok) return null;
        const data = await res.json();
        return (data.access as string) ?? null;
      } catch {
        return null;
      } finally {
        refreshInFlight = null;
      }
    })();
  }
  return refreshInFlight;
}

interface RequestOptions extends RequestInit {
  auth?: boolean; // attach the Bearer access token (default true)
  retry?: boolean; // internal: avoid infinite refresh loops
  parse?: "json" | "blob"; // how to read the body (default JSON)
}

/**
 * Browser -> Django call. Transparently obtains an access token when the
 * session is still bootstrapping, and retries once after a silent refresh
 * when the token has expired (401).
 */
export async function apiFetch<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { auth = true, retry = true, parse = "json", headers, ...rest } = options;

  let token = useAuthStore.getState().accessToken;

  // Components mount and query before the auth bootstrap has finished. Wait
  // for the shared refresh instead of firing a request that would 401 and
  // then trigger a competing refresh.
  if (auth && !token && useAuthStore.getState().status !== "ready") {
    token = await refreshAccessToken();
    if (token) {
      const user = useAuthStore.getState().user;
      if (user) useAuthStore.getState().setSession(token, user);
    }
  }

  const finalHeaders: HeadersInit = { Accept: "application/json", ...headers };

  // L'hébergeur rejette les formulaires de fichiers avant Django : on envoie
  // le même corps multipart sous une autre étiquette. Voir lib/multipart.ts.
  if (rest.body instanceof FormData) {
    const encoded = encodeFormData(rest.body);
    rest.body = encoded.body;
    (finalHeaders as Record<string, string>)["Content-Type"] = UPLOAD_CONTENT_TYPE;
    (finalHeaders as Record<string, string>)[UPLOAD_BOUNDARY_HEADER] = encoded.boundary;
  }

  // Same anonymous id as the SSR calls: Django is on another origin, so its
  // own cookie would be third-party and is not sent here.
  const visitorId = readVisitorCookie();
  if (visitorId) (finalHeaders as Record<string, string>)[VISITOR_HEADER] = visitorId;
  if (auth && token) {
    (finalHeaders as Record<string, string>)["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(new URL(path, API_URL), { ...rest, headers: finalHeaders });

  if (res.status === 401 && auth && retry) {
    const newToken = await refreshAccessToken();
    if (newToken) {
      const user = useAuthStore.getState().user;
      if (user) useAuthStore.getState().setSession(newToken, user);
      return apiFetch<T>(path, { ...options, retry: false });
    }
    useAuthStore.getState().clear();
  }

  if (!res.ok) {
    const body = await safeJson(res);
    throw new ApiError(res.status, body);
  }
  if (res.status === 204) return undefined as T;
  if (parse === "blob") return (await res.blob()) as T;
  return res.json();
}

async function safeJson(res: Response) {
  try {
    return await res.json();
  } catch {
    return null;
  }
}

export { API_URL };
