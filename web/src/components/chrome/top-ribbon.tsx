"use client";

import { useTheme } from "@/providers/theme-provider";
import { useI18n } from "@/providers/i18n-provider";

export function TopRibbon() {
  const { theme } = useTheme();
  const { t } = useI18n();
  const hacker = theme === "hacker";

  const left = hacker
    ? "root@42roma:~$ ./init_campus_network.sh --theme=spqr-cyber"
    : t("ribbon.headline");
  const right = hacker
    ? "[LAT: 41.90411° N // LON: 12.549614° E]"
    : "Via Sandro Sandri, 81 - 00159 Roma";

  return (
    <div
      className="flex items-center justify-between border-b px-6 py-2 font-mono text-[11px] tracking-wide"
      style={{
        background: "var(--ribbon-bg)",
        color: "var(--ribbon-fg)",
        borderColor: hacker ? "var(--primary)" : "var(--border)",
      }}
    >
      <span className="truncate">{left}</span>
      <span className="hidden sm:inline">{right}</span>
    </div>
  );
}
