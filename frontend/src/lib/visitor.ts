/**
 * Anonymous visitor id, shared by the middleware, the SSR fetches and the
 * browser calls. See `src/middleware.ts` for why Next owns this cookie.
 */
export const VISITOR_COOKIE = "nogoya_vid";
export const VISITOR_COOKIE_MAX_AGE = 60 * 60 * 24 * 365; // 1 year
export const VISITOR_HEADER = "X-Visitor-Id";

/** 32 hex characters — anything else is discarded rather than forwarded. */
export function isVisitorId(value: string | undefined | null): value is string {
  return typeof value === "string" && /^[0-9a-f]{32}$/.test(value);
}

/** Reads the id in the browser (the cookie is intentionally not httpOnly). */
export function readVisitorCookie(): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(new RegExp(`(?:^|; )${VISITOR_COOKIE}=([^;]*)`));
  const value = match ? decodeURIComponent(match[1]) : null;
  return isVisitorId(value) ? value : null;
}
