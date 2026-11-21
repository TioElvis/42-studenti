"use client";

import { cn } from "@/lib/utils";
import { CATEGORIES } from "@/lib/categories";
import { useI18n } from "@/providers/i18n-provider";
import type { PostCategory } from "@/lib/types";

export type CategoryFilter = PostCategory | "all";

export function CategoryPills({
  value,
  onChange,
}: {
  value: CategoryFilter;
  onChange: (next: CategoryFilter) => void;
}) {
  const { t } = useI18n();
  const pills: { key: CategoryFilter; label: string }[] = [
    { key: "all", label: t("cat.all") },
    ...CATEGORIES.map((c) => ({ key: c.slug as CategoryFilter, label: t(`cat.${c.slug}`) })),
  ];

  return (
    <div className="flex flex-wrap gap-2" role="tablist" aria-label={t("cat.filter")}>
      {pills.map((pill) => {
        const active = value === pill.key;
        return (
          <button
            key={pill.key}
            type="button"
            role="tab"
            aria-selected={active}
            onClick={() => onChange(pill.key)}
            className={cn(
              "border px-3 py-1.5 font-mono text-xs transition-colors",
              active
                ? "border-[var(--border)] bg-[var(--primary)] text-[var(--primary-fg)] retro-shadow-sm"
                : "border-[var(--border)] bg-[var(--surface)] text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--surface-2)]",
            )}
          >
            {pill.label}
          </button>
        );
      })}
    </div>
  );
}
