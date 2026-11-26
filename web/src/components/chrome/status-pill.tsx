"use client";
import { useI18n } from "@/providers/i18n-provider";

export function StatusPill() {
  const { t } = useI18n();
  return (
    <span className="inline-flex items-center gap-2 border border-[var(--border)] bg-[var(--surface)] px-3 py-1.5 text-[11px] font-[family-name:var(--font-ui)] retro-shadow-sm rounded-[var(--radius-pill)]">
      <span className="status-dot" aria-hidden />
      <span>{t("status.online")}</span>
    </span>
  );
}
