"use client";
import { useTheme } from "@/providers/theme-provider";
import { useI18n } from "@/providers/i18n-provider";
import { cn } from "@/lib/utils";

export function Brand() {
  const { theme } = useTheme();
  const { t } = useI18n();
  const hacker = theme === "hacker";
  const classicModern = theme === "classic-modern";
  const hackerModern = theme === "hacker-modern";
  const green = hacker || hackerModern; // hacker family uses the green "42_" mark
  const badge = classicModern || hackerModern; // modern rounded logo badge

  const subtitle = hacker
    ? "SPQR // HACKER_ROMAN_PALETTE"
    : hackerModern
      ? "SPQR // Cluster Roma · 41.90411° N, 12.549614° E"
      : t("brand.subtitle");

  return (
    <div className="flex items-center gap-3.5">
      <div
        className={cn(
          "font-display font-bold leading-none",
          badge
            ? "flex h-12 w-12 items-center justify-center rounded-[14px] border text-xl"
            : "text-3xl",
        )}
        style={{
          color: classicModern
            ? "var(--primary-fg)"
            : green
              ? "var(--status-online)"
              : "var(--primary)",
          textShadow: green ? "var(--glow)" : "none",
          background: classicModern
            ? "var(--primary)"
            : hackerModern
              ? "rgba(0, 255, 136, 0.1)"
              : "transparent",
          borderColor: classicModern
            ? "transparent"
            : hackerModern
              ? "rgba(0, 255, 136, 0.4)"
              : "var(--border)",
          boxShadow: classicModern
            ? "0 6px 16px rgba(155, 41, 40, 0.25)"
            : hackerModern
              ? "0 0 24px rgba(0, 255, 136, 0.15)"
              : undefined,
        }}
      >
        {green ? "42_" : "42"}
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
