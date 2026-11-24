"use client";

import { cn } from "@/lib/utils";
import { useI18n } from "@/providers/i18n-provider";

/** "Interno 42" vs "Esterno" badge — themed via tokens (works in both themes). */
export function EventScopeBadge({
  internal,
  className,
}: {
  internal: boolean;
  className?: string;
}) {
  const { t } = useI18n();
  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center border px-2 py-0.5 font-mono text-[10px] font-bold uppercase tracking-wide",
        internal
          ? "border-[var(--border)] bg-[var(--primary)] text-[var(--primary-fg)]"
          : "border-[var(--border)] bg-[var(--surface-2)] text-[var(--text-muted)]",
        className,
      )}
    >
      {internal ? t("eventi.internal") : t("eventi.external")}
    </span>
  );
}
