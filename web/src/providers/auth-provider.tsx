"use client";

import * as React from "react";

import { api, ApiError } from "@/lib/api";
import { disablePush } from "@/lib/push";
import type { UserMe } from "@/lib/types";

/** `waking`: the API is unreachable/slow (e.g. a sleeping host) — we show the
 * dedicated wake screen and poll /health until it answers. */
type AuthStatus = "loading" | "waking" | "authenticated" | "anonymous";

interface AuthContextValue {
  status: AuthStatus;
  user: UserMe | null;
  refresh: () => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = React.createContext<AuthContextValue | null>(null);

// If /me hasn't answered after this long, show the wake screen instead of a
// plain spinner (a cold-started host can take up to a minute).
const SLOW_MS = 3_000;
// Longest the logout waits for this browser's notifications to be turned off.
const PUSH_LOGOUT_MS = 3_000;
// Gentle backoff between /health probes while the API wakes up.
const POLL_DELAYS_MS = [2_000, 3_000, 5_000];

/** Network failure, timeout, or a gateway error from a host that is still booting. */
function isWakeError(err: unknown): boolean {
  if (err instanceof ApiError) return [502, 503, 504].includes(err.status);
  return true; // fetch rejected (offline, refused, aborted)
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = React.useState<AuthStatus>("loading");
  const [user, setUser] = React.useState<UserMe | null>(null);
  // Only the latest refresh may apply its result; also stops polling on unmount.
  const reqRef = React.useRef(0);
  const aliveRef = React.useRef(true);

  const refresh = React.useCallback(async () => {
    const id = ++reqRef.current;
    const slow = setTimeout(() => {
      if (id === reqRef.current) setStatus((s) => (s === "loading" ? "waking" : s));
    }, SLOW_MS);
    try {
      const me = await api.me();
      if (id !== reqRef.current) return;
      setUser(me);
      setStatus("authenticated");
    } catch (err) {
      if (id !== reqRef.current) return;
      setUser(null);
      if (err instanceof ApiError && err.status === 401) {
        setStatus("anonymous");
      } else if (isWakeError(err)) {
        setStatus("waking");
        void waitForApi(id);
      } else {
        setStatus("anonymous");
      }
    } finally {
      clearTimeout(slow);
    }

    // Poll /health with backoff; once it answers, retry the session check.
    async function waitForApi(forId: number) {
      for (let i = 0; aliveRef.current && forId === reqRef.current; i++) {
        const delay = POLL_DELAYS_MS[Math.min(i, POLL_DELAYS_MS.length - 1)]!;
        await new Promise((r) => setTimeout(r, delay));
        if (!aliveRef.current || forId !== reqRef.current) return;
        if (await api.health()) {
          void refresh();
          return;
        }
      }
    }
  }, []);

  const logout = React.useCallback(async () => {
    try {
      // While still logged in, so the server can forget this browser. A slow or
      // failing push service must not block the logout.
      await Promise.race([
        disablePush().catch(() => {}),
        new Promise((resolve) => setTimeout(resolve, PUSH_LOGOUT_MS)),
      ]);
      await api.logout();
    } finally {
      setUser(null);
      setStatus("anonymous");
    }
  }, []);

  React.useEffect(() => {
    aliveRef.current = true;
    void refresh();
    return () => {
      aliveRef.current = false;
    };
  }, [refresh]);

  const value = React.useMemo(
    () => ({ status, user, refresh, logout }),
    [status, user, refresh, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = React.useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within <AuthProvider>");
  return ctx;
}
