"use client";

import * as React from "react";

import { Button } from "@/components/ui/button";
import { useAuth } from "@/providers/auth-provider";
import { useI18n } from "@/providers/i18n-provider";

const EXPLAIN_AFTER_S = 15; // explain the free-hosting cold start
const RETRY_AFTER_S = 90; // offer a manual retry

/** Dedicated page shown while the API (a sleeping host) wakes up. It keeps
 * probing /health in the background (see AuthProvider) and switches to the app
 * by itself as soon as the server answers. */
export function WakeScreen() {
  const { t } = useI18n();
  const { refresh } = useAuth();
  const [seconds, setSeconds] = React.useState(0);

  React.useEffect(() => {
    const started = Date.now();
    const id = setInterval(() => setSeconds(Math.floor((Date.now() - started) / 1000)), 1000);
    return () => clearInterval(id);
  }, []);

  const mm = String(Math.floor(seconds / 60)).padStart(2, "0");
  const ss = String(seconds % 60).padStart(2, "0");

  return (
    <div
      className="flex min-h-screen flex-col items-center justify-center gap-5 px-6 text-center"
      role="status"
      aria-live="polite"
    >
      <div className="font-display text-6xl font-bold" style={{ color: "var(--primary)" }}>
        42
      </div>
      <h1 className="font-display text-xl font-bold">{t("wake.title")}</h1>
      <p className="max-w-md font-mono text-sm text-[var(--text-muted)]">
        {t("wake.body")}
        <span className="cursor-blink">_</span>
      </p>

      {/* Indeterminate bar: we can't know how long the host needs. */}
      <div
        className="h-1.5 w-64 max-w-full overflow-hidden border border-[var(--border)] bg-[var(--surface-2)] rounded-[var(--radius-pill)]"
        aria-hidden
      >
        <div className="wake-bar h-full w-1/3 bg-[var(--primary)]" />
      </div>

      <p className="font-mono text-xs tabular-nums text-[var(--text-muted)]">
        {t("wake.elapsed", { time: `${mm}:${ss}` })}
      </p>

      {seconds >= EXPLAIN_AFTER_S && (
        <p className="max-w-md font-mono text-xs text-[var(--text-muted)]">{t("wake.explain")}</p>
      )}

      {seconds >= RETRY_AFTER_S && (
        <div className="flex flex-col items-center gap-2">
          <p className="font-mono text-xs text-[var(--primary)]">{t("wake.slow")}</p>
          <Button variant="outline" size="sm" onClick={() => void refresh()}>
            {t("common.retry")}
          </Button>
        </div>
      )}
    </div>
  );
}
