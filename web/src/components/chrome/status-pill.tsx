"use client";
import { useTheme } from "@/providers/theme-provider";
import { useI18n } from "@/providers/i18n-provider";

export function StatusPill() {
  const { theme } = useTheme();
  const { t } = useI18n();
  const label = theme === "hacker" ? "NODE_ONLINE :: 42_INTRA_SYNCED" : t("status.online");
  return (
    <span className="inline-flex items-center gap-2 border border-[var(--border)] bg-[var(--surface)] px-3 py-1.5 text-[11px] font-mono retro-shadow-sm">
      <span className="status-dot" aria-hidden />
      <span>{label}</span>
    </span>
  );
}
