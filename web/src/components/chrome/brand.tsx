"use client";
import { useTheme } from "@/providers/theme-provider";
import { useI18n } from "@/providers/i18n-provider";

export function Brand() {
  const { theme } = useTheme();
  const { t } = useI18n();
  const hacker = theme === "hacker";
  const subtitle = hacker ? "SPQR // HACKER_ROMAN_PALETTE" : t("brand.subtitle");

  return (
    <div className="flex items-center gap-3.5">
      <div
        className="font-display text-3xl font-bold leading-none"
        style={{
          color: hacker ? "var(--status-online)" : "var(--primary)",
          textShadow: hacker ? "var(--glow)" : "none",
        }}
      >
        {hacker ? "42_" : "42"}
      </div>
      <div>
        <span className="font-[family-name:var(--font-ui)] text-sm font-bold tracking-wide">
          {hacker ? "STUDENTI.EXE" : "STUDENTI"}
        </span>
        <div className="font-mono text-xs text-[var(--text-muted)]">{subtitle}</div>
      </div>
    </div>
  );
}
