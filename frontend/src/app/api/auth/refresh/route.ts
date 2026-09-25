import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { API_URL } from "@/lib/server-api";
import { REFRESH_COOKIE, refreshCookieOptions } from "@/lib/auth-cookies";
import { callUpstream } from "@/lib/upstream";

/**
 * Silent refresh: reads the httpOnly refresh cookie, exchanges it for a new
 * access token, and rotates the refresh cookie (SIMPLE_JWT ROTATE_REFRESH_TOKENS).
 * Called on app bootstrap and whenever a Bearer-authed API call gets a 401.
 */
export async function POST() {
  const store = await cookies();
  const refresh = store.get(REFRESH_COOKIE)?.value;
  if (!refresh) {
    return NextResponse.json({ detail: "Aucune session." }, { status: 401 });
  }

  const { ok, status, data } = await callUpstream(`${API_URL}/api/v1/auth/refresh/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh }),
  });

  if (!ok) {
    const response = NextResponse.json(data, { status });
    // A 5xx is the API's problem, not a dead session: keep the cookie so the
    // next attempt can still restore it.
    if (status < 500) response.cookies.delete(REFRESH_COOKIE);
    return response;
  }

  const { access, refresh: rotated } = data as { access: string; refresh?: string };
  const response = NextResponse.json({ access });
  if (rotated) {
    response.cookies.set(REFRESH_COOKIE, rotated, refreshCookieOptions);
  }
  return response;
}
