"use client";

import * as React from "react";

import { useAuth } from "./auth-provider";
import type { RealtimeEvent } from "@/lib/types";

type Handler = (event: RealtimeEvent) => void;

interface RealtimeContextValue {
  subscribe: (handler: Handler) => () => void;
}

const RealtimeContext = React.createContext<RealtimeContextValue | null>(null);

function websocketUrl(): string {
  const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:9000";
  const url = new URL(base);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  url.pathname = url.pathname.replace(/\/$/, "") + "/ws";
  url.search = "";
  return url.toString();
}

/**
 * Opens one authenticated WebSocket while a student is logged in and fans each
 * incoming event out to subscribers. Reconnects with exponential backoff and
 * closes cleanly on logout/unmount.
 */
export function RealtimeProvider({ children }: { children: React.ReactNode }) {
  const { status } = useAuth();
  const listeners = React.useRef<Set<Handler>>(new Set());

  const subscribe = React.useCallback((handler: Handler) => {
    listeners.current.add(handler);
    return () => {
      listeners.current.delete(handler);
    };
  }, []);

  React.useEffect(() => {
    if (status !== "authenticated") return;

    let socket: WebSocket | null = null;
    let disposed = false;
    let attempt = 0;
    let retryTimer: ReturnType<typeof setTimeout> | undefined;

    const connect = () => {
      if (disposed) return;
      try {
        socket = new WebSocket(websocketUrl());
      } catch {
        scheduleRetry();
        return;
      }
      socket.onopen = () => {
        attempt = 0;
      };
      socket.onmessage = (ev) => {
        let parsed: RealtimeEvent;
        try {
          parsed = JSON.parse(ev.data) as RealtimeEvent;
        } catch {
          return;
        }
        listeners.current.forEach((handler) => {
          try {
            handler(parsed);
          } catch {
            /* a bad subscriber must not break the others */
          }
        });
      };
      socket.onclose = () => {
        if (!disposed) scheduleRetry();
      };
      socket.onerror = () => {
        try {
          socket?.close();
        } catch {
          /* ignore */
        }
      };
    };

    const scheduleRetry = () => {
      const delay = Math.min(1000 * 2 ** attempt, 15000);
      attempt += 1;
      retryTimer = setTimeout(connect, delay);
    };

    connect();

    return () => {
      disposed = true;
      if (retryTimer) clearTimeout(retryTimer);
      try {
        socket?.close();
      } catch {
        /* ignore */
      }
    };
  }, [status]);

  const value = React.useMemo(() => ({ subscribe }), [subscribe]);
  return <RealtimeContext.Provider value={value}>{children}</RealtimeContext.Provider>;
}

/** Subscribe to live events. The latest `handler` is always used (no stale closures). */
export function useRealtime(handler: Handler): void {
  const ctx = React.useContext(RealtimeContext);
  const ref = React.useRef(handler);
  ref.current = handler;

  React.useEffect(() => {
    if (!ctx) return;
    return ctx.subscribe((event) => ref.current(event));
  }, [ctx]);
}
