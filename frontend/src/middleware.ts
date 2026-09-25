import { NextResponse, type NextRequest } from "next/server";
import { VISITOR_COOKIE, VISITOR_COOKIE_MAX_AGE, isVisitorId } from "@/lib/visitor";

/**
 * Mints the anonymous visitor id on *our* domain.
 *
 * Django also knows how to set this cookie, but it never can for real
 * browsers: pages are server-rendered, so the browser only ever talks to
 * Next.js and Django's `Set-Cookie` dies in the server-to-server hop. Left
 * alone, every page view invented a brand new visitor id, which silently
 * broke view-count de-duplication and "Vus récemment". Owning the cookie
 * here makes the id stable for both the SSR fetches and the browser calls.
 *
 * The value is a random opaque id — no IP, no fingerprint, nothing personal.
 * It is deliberately readable by JavaScript so client-side API calls can send
 * the same id as `X-Visitor-Id`.
 */
export function middleware(request: NextRequest) {
  const existing = request.cookies.get(VISITOR_COOKIE)?.value;
  if (existing && isVisitorId(existing)) return NextResponse.next();

  const visitorId = crypto.randomUUID().replace(/-/g, "");
  // Make it visible to this render too, not just to the next request.
  const headers = new Headers(request.headers);
  headers.set("cookie", [request.headers.get("cookie"), `${VISITOR_COOKIE}=${visitorId}`].filter(Boolean).join("; "));

  const response = NextResponse.next({ request: { headers } });
  response.cookies.set(VISITOR_COOKIE, visitorId, {
    maxAge: VISITOR_COOKIE_MAX_AGE,
    sameSite: "lax",
    path: "/",
    secure: process.env.NODE_ENV === "production",
  });
  return response;
}

export const config = {
  // Everything except Next internals and static assets.
  matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp|ico)$).*)"],
};
