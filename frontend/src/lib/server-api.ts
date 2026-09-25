import "server-only";

import { cookies } from "next/headers";
import { VISITOR_COOKIE, VISITOR_HEADER, isVisitorId } from "./visitor";

const API_URL = process.env.API_URL ?? "http://127.0.0.1:8000";

/**
 * Server-to-server fetch against the Django API — used from Server Components
 * and Route Handlers. No auth: only ever call public, read-only endpoints here.
 */
export async function apiGet<T>(
  path: string,
  params?: Record<string, string | undefined>,
  init?: RequestInit
): Promise<T> {
  const url = new URL(path, API_URL);
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== "") url.searchParams.set(key, value);
    }
  }
  const res = await fetch(url.toString(), {
    ...init,
    headers: { Accept: "application/json", ...init?.headers },
  });
  if (!res.ok) {
    throw new ApiError(res.status, await safeJson(res));
  }
  return res.json();
}

/**
 * Forwards this browser's anonymous visitor id to Django.
 *
 * Server-to-server fetches carry no cookies, so without this header the API
 * sees a brand new visitor on every render — breaking view de-duplication and
 * the "recently viewed" history. Only pass it to endpoints that record
 * analytics: reading the cookie opts the route into dynamic rendering.
 */
export async function visitorHeaders(): Promise<Record<string, string>> {
  const value = (await cookies()).get(VISITOR_COOKIE)?.value;
  return isVisitorId(value) ? { [VISITOR_HEADER]: value } : {};
}

export class ApiError extends Error {
  status: number;
  body: unknown;
  constructor(status: number, body: unknown) {
    super(`API error ${status}`);
    this.status = status;
    this.body = body;
  }
}

async function safeJson(res: Response) {
  try {
    return await res.json();
  } catch {
    return null;
  }
}

export { API_URL };
