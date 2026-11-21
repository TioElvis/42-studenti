"use client";

import { useTheme } from "@/providers/theme-provider";
import { useI18n } from "@/providers/i18n-provider";

export function TopRibbon() {
  const { theme } = useTheme();
  const { t } = useI18n();
  const hacker = theme === "hacker";

  return (
    <div
      className="flex items-center justify-between border-b px-6 py-2 font-mono text-[11px] tracking-wide"
      style={{
        background: "var(--ribbon-bg)",
        color: "var(--ribbon-fg)",
        borderColor: hacker ? "var(--primary)" : "var(--border)",
      }}
    >
      {hacker ? (
        <>
          <span className="truncate">root@42roma:~$ ./init_campus_network.sh --theme=spqr-cyber</span>
          <span className="hidden sm:inline">[LAT: 41.90411° N // LON: 12.549614° E]</span>
        </>
      ) : (
        <>
          <span className="truncate">{t("ribbon.headline")}</span>
          <span className="hidden sm:inline">Via Sandro Sandri, 81 - 00159 Roma</span>
        </>
      )}
    </div>
  );
}
