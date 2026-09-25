import { render, screen, waitFor } from "@testing-library/react";
import { useState } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AuthProvider, useAuth } from "./AuthProvider";
import { useAuthStore } from "@/store/auth-store";

const apiFetch = vi.hoisted(() => vi.fn());
vi.mock("@/lib/client-api", async () => {
  // Keep the real refreshAccessToken: the bootstrap and apiFetch share it,
  // and these tests exercise exactly that coordination.
  const actual = await vi.importActual<typeof import("@/lib/client-api")>("@/lib/client-api");
  return { ...actual, apiFetch };
});

function LoginProbe() {
  const { login } = useAuth();
  const user = useAuthStore((s) => s.user);
  const [error, setError] = useState<string | null>(null);
  return (
    <div>
      <button
        onClick={() =>
          login("+22670010001", "DemoPass123!").catch((err: Error) => setError(err.message))
        }
      >
        login
      </button>
      <span data-testid="user">{user ? user.full_name : "anonymous"}</span>
      <span data-testid="error">{error}</span>
    </div>
  );
}

describe("AuthProvider", () => {
  beforeEach(() => {
    useAuthStore.setState({ user: null, accessToken: null, status: "idle" });
  });

  it("restores a session from the httpOnly refresh cookie on mount", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.includes("/api/auth/refresh")) {
          return new Response(JSON.stringify({ access: "token" }), { status: 200 });
        }
        return new Response(
          JSON.stringify({ id: 1, role: "supplier", first_name: "Issa", last_name: "O", phone: "+226" }),
          { status: 200 }
        );
      })
    );

    render(
      <AuthProvider>
        <LoginProbe />
      </AuthProvider>
    );

    await waitFor(() => expect(screen.getByTestId("user")).toHaveTextContent("Issa O"));
  });

  it("stays anonymous when there is no cookie", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response("{}", { status: 401 })));

    render(
      <AuthProvider>
        <LoginProbe />
      </AuthProvider>
    );

    await waitFor(() => expect(useAuthStore.getState().status).toBe("ready"));
    expect(screen.getByTestId("user")).toHaveTextContent("anonymous");
  });

  it("explains a restarting API instead of leaking a JSON parse error", async () => {
    // An empty body used to surface as "Failed to execute 'json' on
    // 'Response': Unexpected end of JSON input", right in the login form.
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.includes("/api/auth/login")) return new Response("", { status: 502 });
        return new Response("{}", { status: 401 });
      })
    );

    render(
      <AuthProvider>
        <LoginProbe />
      </AuthProvider>
    );
    screen.getByRole("button", { name: "login" }).click();

    await waitFor(() =>
      expect(screen.getByTestId("error")).toHaveTextContent(/Connexion au service impossible/)
    );
  });

  it("tells the person to wait when the login endpoint rate-limits them", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.includes("/api/auth/login")) {
          return new Response(
            JSON.stringify({ detail: "Trop de tentatives. Patientez une minute avant de réessayer." }),
            { status: 429 }
          );
        }
        return new Response("{}", { status: 401 });
      })
    );

    render(
      <AuthProvider>
        <LoginProbe />
      </AuthProvider>
    );
    screen.getByRole("button", { name: "login" }).click();

    await waitFor(() => expect(screen.getByTestId("error")).toHaveTextContent(/Patientez une minute/));
  });

  it("does not wipe a session established while the bootstrap was in flight", async () => {
    // The bootstrap refresh resolves *after* the user has logged in — it must
    // not clear the fresher session (regression caught by the E2E suite).
    let releaseBootstrap: (value: Response) => void = () => {};
    const bootstrapPending = new Promise<Response>((resolve) => {
      releaseBootstrap = resolve;
    });
    let refreshCalls = 0;

    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.includes("/api/auth/refresh")) {
          refreshCalls += 1;
          return refreshCalls === 1 ? bootstrapPending : new Response("{}", { status: 401 });
        }
        if (url.includes("/api/auth/login")) {
          return new Response(
            JSON.stringify({ access: "fresh", user: { id: 7, role: "visitor", full_name: "Fatou K" } }),
            { status: 200 }
          );
        }
        return new Response("{}", { status: 200 });
      })
    );

    render(
      <AuthProvider>
        <LoginProbe />
      </AuthProvider>
    );

    screen.getByRole("button", { name: "login" }).click();
    await waitFor(() => expect(screen.getByTestId("user")).toHaveTextContent("Fatou K"));

    // now let the stale bootstrap request fail
    releaseBootstrap(new Response("{}", { status: 401 }));

    await waitFor(() => expect(useAuthStore.getState().status).toBe("ready"));
    expect(useAuthStore.getState().user?.full_name).toBe("Fatou K");
  });
});
