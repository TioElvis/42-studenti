"use client";

import { useTheme } from "@/providers/theme-provider";
import { useI18n } from "@/providers/i18n-provider";

export function TopRibbon() {
  const { theme } = useTheme();
  const { t } = useI18n();
  const hacker = theme === "hacker";
  const hackerModern = theme === "hacker-modern";

  return (
    <div
      className="flex items-center justify-between border-b px-6 py-2 font-mono text-[11px] tracking-wide"
      style={{
        background: "var(--ribbon-bg)",
        color: "var(--ribbon-fg)",
        borderColor: hacker ? "var(--primary)" : "var(--border-subtle)",
        backdropFilter: hackerModern ? "blur(12px)" : undefined,
      }}
    >
      <span className="truncate" style={hackerModern ? { color: "var(--primary)" } : undefined}>
        {t("ribbon.headline")}
      </span>
      <span className="hidden sm:inline">Via Sandro Sandri, 81 - 00159 Roma</span>
    </div>
  );
}
