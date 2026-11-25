"use client";
import { useTheme, type Theme } from "@/providers/theme-provider";
import { useI18n } from "@/providers/i18n-provider";

export function StatusPill() {
  const { theme } = useTheme();
  const { t } = useI18n();
  // Each theme has its own flavor: classic or terminal flavor (retro or modern).
  const labels: Record<Theme, string> = {
    classic: t("status.online"),
    hacker: "NODE_ONLINE :: 42_INTRA_SYNCED",
    "classic-modern": t("status.online"),
    "hacker-modern": "NODE_ONLINE :: 42_SYNC",
  };
  return (
    <span className="inline-flex items-center gap-2 border border-[var(--border)] bg-[var(--surface)] px-3 py-1.5 text-[11px] font-[family-name:var(--font-ui)] retro-shadow-sm rounded-[var(--radius-pill)]">
      <span className="status-dot" aria-hidden />
      <span>{labels[theme]}</span>
    </span>
  );
}
