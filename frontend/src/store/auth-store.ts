import { create } from "zustand";
import type { Role } from "@/lib/types";

export interface SessionUser {
  id: number;
  role: Role;
  full_name: string;
}

interface AuthState {
  accessToken: string | null;
  user: SessionUser | null;
  status: "idle" | "loading" | "ready";
  setSession: (accessToken: string, user: SessionUser) => void;
  clear: () => void;
  setStatus: (status: AuthState["status"]) => void;
}

/**
 * Access token lives in memory only (never localStorage) to limit the blast
 * radius of an XSS bug. The refresh token is an httpOnly cookie the browser
 * never sees; see src/app/api/auth/* route handlers.
 */
export const useAuthStore = create<AuthState>((set) => ({
  accessToken: null,
  user: null,
  status: "idle",
  setSession: (accessToken, user) => set({ accessToken, user, status: "ready" }),
  clear: () => set({ accessToken: null, user: null, status: "ready" }),
  setStatus: (status) => set({ status }),
}));
