"use client";

import { refreshAccessToken } from "@/lib/client-api";
import { useAuthStore } from "@/store/auth-store";
import { VISITOR_HEADER, readVisitorCookie } from "@/lib/visitor";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export interface UploadHandle {
  /** Resolves with the parsed response, rejects on failure or cancellation. */
  done: Promise<unknown>;
  cancel: () => void;
}

export class UploadError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

/**
 * POST a multipart body and report how far it got.
 *
 * `fetch` cannot do this: it has no upload progress event, so a person
 * sending a 40 MB video over a slow connection would stare at a spinner with
 * no idea whether anything was happening. XMLHttpRequest still does, and it
 * can be aborted, which is the other half of the requirement.
 */
export function uploadWithProgress(
  path: string,
  body: FormData,
  onProgress: (percent: number) => void
): UploadHandle {
  const request = new XMLHttpRequest();

  const done = (async () => {
    let token = useAuthStore.getState().accessToken;
    if (!token) token = await refreshAccessToken();

    return new Promise((resolve, reject) => {
      request.open("POST", new URL(path, API_URL).toString());
      request.setRequestHeader("Accept", "application/json");
      if (token) request.setRequestHeader("Authorization", `Bearer ${token}`);
      const visitorId = readVisitorCookie();
      if (visitorId) request.setRequestHeader(VISITOR_HEADER, visitorId);

      request.upload.onprogress = (event) => {
        if (event.lengthComputable) {
          onProgress(Math.round((event.loaded / event.total) * 100));
        }
      };

      request.onload = () => {
        let payload: unknown = null;
        try {
          payload = request.responseText ? JSON.parse(request.responseText) : null;
        } catch {
          payload = null;
        }
        if (request.status >= 200 && request.status < 300) {
          resolve(payload);
          return;
        }
        const detail =
          (payload as { detail?: string } | null)?.detail ??
          (request.status === 413
            ? "Fichier trop volumineux."
            : "L'envoi a échoué. Réessayez.");
        reject(new UploadError(request.status, detail));
      };

      request.onerror = () =>
        reject(new UploadError(0, "Connexion interrompue pendant l'envoi."));
      request.onabort = () => reject(new UploadError(0, "Envoi annulé."));

      request.send(body);
    });
  })();

  return { done, cancel: () => request.abort() };
}
