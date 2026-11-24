"use client";
import { useTheme } from "@/providers/theme-provider";
import { useI18n } from "@/providers/i18n-provider";
import { cn } from "@/lib/utils";

export function Brand() {
  const { theme } = useTheme();
  const { t } = useI18n();
  const hacker = theme === "hacker";
  const bento = theme === "bento";
  const bentoHacker = theme === "bento-hacker";
  // "Hacker" family (retro + modern) uses the green "42_" mark; others plain.
  const green = hacker || bentoHacker;
  const badge = bentoHacker; // modern glass logo badge

  const subtitle = hacker
    ? "SPQR // HACKER_ROMAN_PALETTE"
    : bentoHacker
      ? "SPQR // Cluster Roma · 41.90411° N, 12.549614° E"
      : t("brand.subtitle");

  return (
    <div className="flex items-center gap-3.5">
      <div
        className={cn(
          "font-display font-bold leading-none",
          badge ? "text-2xl rounded-[10px] border px-2.5 py-1" : "text-3xl",
        )}
        style={{
          color: green ? "var(--status-online)" : "var(--primary)",
          textShadow: green ? "var(--glow)" : "none",
          background: badge ? "var(--surface-2)" : "transparent",
          borderColor: bentoHacker ? "rgba(0, 255, 136, 0.35)" : "var(--border)",
        }}
      >
        {green ? "42_" : "42"}
      </div>
      <div>
        <div className="flex items-center gap-2">
          <span className="font-[family-name:var(--font-ui)] text-sm font-bold tracking-wide">
            {hacker ? "STUDENTI.EXE" : "STUDENTI"}
          </span>
          {bento && (
            <span className="rounded-full border border-[var(--cat-cerco_team-fg)] bg-[var(--cat-cerco_team-bg)] px-2 py-0.5 text-[10px] font-semibold text-[var(--cat-cerco_team-fg)]">
              Roma
            </span>
          )}
        </div>
        <div className="font-mono text-xs text-[var(--text-muted)]">{subtitle}</div>
      </div>
    </div>
  );
}
