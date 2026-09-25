import "server-only";

/**
 * Calls the Django API from a Route Handler without ever assuming the
 * answer is JSON.
 *
 * A restarting API, a proxy error page or a rate-limit response can all come
 * back empty or as HTML. `await response.json()` then throws, and the raw
 * "Unexpected end of JSON input" ended up displayed in the login form.
 */
export async function callUpstream(url: string, init: RequestInit) {
  let upstream: Response;
  try {
    upstream = await fetch(url, init);
  } catch {
    return {
      ok: false,
      status: 502,
      data: { detail: "Service momentanément indisponible. Réessayez dans un instant." },
    };
  }

  const raw = await upstream.text();
  let data: Record<string, unknown>;
  try {
    data = raw ? JSON.parse(raw) : {};
  } catch {
    data = {};
  }

  if (!upstream.ok && !data.detail && !Object.keys(data).length) {
    data = { detail: upstreamMessage(upstream.status) };
  }
  return { ok: upstream.ok, status: upstream.status, data };
}

function upstreamMessage(status: number) {
  if (status === 429) return "Trop de tentatives. Patientez une minute avant de réessayer.";
  if (status >= 500) return "Service momentanément indisponible. Réessayez dans un instant.";
  return "Requête refusée.";
}
