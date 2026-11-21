"use client";

import { useI18n } from "@/providers/i18n-provider";

/** Shown while we check the session (GET /me). Terminal boot vibe. */
export function BootScreen() {
  const { t } = useI18n();
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-3 px-6 text-center">
      <div className="font-display text-4xl font-bold" style={{ color: "var(--primary)" }}>
        42
      </div>
      <p className="font-mono text-sm text-[var(--text-muted)]">
        {t("boot.connecting")}
        <span className="cursor-blink">_</span>
      </p>
    </div>
  );
}
