import { NextResponse } from "next/server";
import { API_URL, visitorHeaders } from "@/lib/server-api";
import { REFRESH_COOKIE, refreshCookieOptions } from "@/lib/auth-cookies";
import { callUpstream } from "@/lib/upstream";

/**
 * BFF login: the browser never sees the refresh token. We call Django,
 * strip the refresh token out of the JSON, and store it as an httpOnly
 * cookie instead. Only the short-lived access token reaches client JS.
 */
export async function POST(request: Request) {
  const body = await request.json();
  const { ok, status, data } = await callUpstream(`${API_URL}/api/v1/auth/login/`, {
    method: "POST",
    // Forward the visitor id: the API rate-limits these endpoints per
    // browser, and every call from here carries this server's address.
    headers: { "Content-Type": "application/json", ...(await visitorHeaders()) },
    body: JSON.stringify(body),
  });

  if (!ok) {
    return NextResponse.json(data, { status });
  }

  const { refresh, ...rest } = data as { refresh: string } & Record<string, unknown>;
  const response = NextResponse.json(rest);
  response.cookies.set(REFRESH_COOKIE, refresh, refreshCookieOptions);
  return response;
}
