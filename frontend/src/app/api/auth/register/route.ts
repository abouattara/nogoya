import { NextResponse } from "next/server";
import { API_URL, visitorHeaders } from "@/lib/server-api";
import { callUpstream } from "@/lib/upstream";

export async function POST(request: Request) {
  const body = await request.json();
  const { status, data } = await callUpstream(`${API_URL}/api/v1/auth/register/`, {
    method: "POST",
    // Forward the visitor id: the API rate-limits these endpoints per
    // browser, and every call from here carries this server's address.
    headers: { "Content-Type": "application/json", ...(await visitorHeaders()) },
    body: JSON.stringify(body),
  });
  return NextResponse.json(data, { status });
}
