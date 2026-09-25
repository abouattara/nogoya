import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { API_URL } from "@/lib/server-api";
import { REFRESH_COOKIE } from "@/lib/auth-cookies";
import { VISITOR_COOKIE } from "@/lib/visitor";

export async function POST() {
  const store = await cookies();
  const refresh = store.get(REFRESH_COOKIE)?.value;
  if (refresh) {
    await fetch(`${API_URL}/api/v1/auth/logout/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh }),
    }).catch(() => undefined); // best-effort; the cookie is cleared regardless
  }
  const response = NextResponse.json({ ok: true });
  response.cookies.delete(REFRESH_COOKIE);
  // Rotate the anonymous id too: on a shared device the next person must not
  // inherit this account's browsing history in their suggestions.
  response.cookies.delete(VISITOR_COOKIE);
  return response;
}
