"use client";

import { createContext, useContext, useEffect, useRef, type ReactNode } from "react";
import { refreshAccessToken } from "@/lib/client-api";
import { useAuthStore, type SessionUser } from "@/store/auth-store";
import type { Me } from "@/lib/types";

interface AuthContextValue {
  login: (phone: string, password: string) => Promise<void>;
  register: (payload: RegisterPayload) => Promise<void>;
  logout: () => Promise<void>;
}

interface RegisterPayload {
  phone: string;
  first_name: string;
  last_name: string;
  role: "visitor" | "supplier";
  password: string;
  password2: string;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const setSession = useAuthStore((s) => s.setSession);
  const clear = useAuthStore((s) => s.clear);
  const setStatus = useAuthStore((s) => s.setStatus);
  const bootstrapped = useRef(false);

  useEffect(() => {
    if (bootstrapped.current) return;
    bootstrapped.current = true;
    (async () => {
      setStatus("loading");
      try {
        // Shared with client-api: the refresh token rotates on every use,
        // so all refreshes in the app must funnel through one promise.
        const access = await refreshAccessToken();
        if (!access) throw new Error("no session");
        const me = await apiFetchWithToken<Me>("/api/v1/auth/me/", access);
        // A login may have completed while this bootstrap was in flight
        // (fast form submit right after page load). Don't overwrite the
        // fresher session with this one.
        if (useAuthStore.getState().user) {
          setStatus("ready");
          return;
        }
        setSession(access, { id: me.id, role: me.role, full_name: `${me.first_name} ${me.last_name}`.trim() || me.phone });
      } catch {
        // Same race, failure side: signing in during the bootstrap must not
        // be undone by this request finding no (or a rotated) cookie.
        if (useAuthStore.getState().user) {
          setStatus("ready");
          return;
        }
        clear();
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const value: AuthContextValue = {
    async login(phone, password) {
      const { ok, status, data } = await postJson("/api/auth/login", { phone, password });
      if (!ok) throw new Error(readDetail(data) ?? fallbackMessage(status));
      setSession(data.access as string, data.user as SessionUser);
    },
    async register(payload) {
      const { ok, status, data } = await postJson("/api/auth/register", payload);
      if (!ok) {
        // Field errors come back as {field: [messages]}; anything else is a
        // transport problem and deserves a sentence, not a raw exception.
        const detail = readDetail(data);
        if (detail || !Object.keys(data).length) {
          throw new RegisterError({ non_field_errors: [detail ?? fallbackMessage(status)] });
        }
        throw new RegisterError(data as Record<string, string[]>);
      }
    },
    async logout() {
      await fetch("/api/auth/logout", { method: "POST" });
      clear();
    },
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

/**
 * POSTs JSON and never assumes the answer is JSON.
 *
 * A restarting API returns an empty body; `res.json()` then throws, and the
 * raw "Unexpected end of JSON input" was shown to the person trying to sign
 * in. Transport failures deserve a sentence they can act on.
 */
async function postJson(url: string, payload: unknown) {
  let res: Response;
  try {
    res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch {
    return { ok: false, status: 0, data: {} as Record<string, unknown> };
  }
  const raw = await res.text();
  let data: Record<string, unknown> = {};
  try {
    data = raw ? JSON.parse(raw) : {};
  } catch {
    data = {};
  }
  return { ok: res.ok, status: res.status, data };
}

function readDetail(data: Record<string, unknown>) {
  const detail = data.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && typeof detail[0] === "string") return detail[0];
  return null;
}

function fallbackMessage(status: number) {
  if (status === 401 || status === 400) return "Identifiants invalides.";
  if (status === 429) return "Trop de tentatives. Patientez une minute avant de réessayer.";
  return "Connexion au service impossible. Réessayez dans un instant.";
}

export class RegisterError extends Error {
  fields: Record<string, string[]>;
  constructor(fields: Record<string, string[]>) {
    super("Inscription invalide.");
    this.fields = fields;
  }
}

async function apiFetchWithToken<T>(path: string, token: string): Promise<T> {
  const base = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
  const res = await fetch(new URL(path, base), {
    headers: { Authorization: `Bearer ${token}`, Accept: "application/json" },
  });
  if (!res.ok) throw new Error("me fetch failed");
  return res.json();
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
