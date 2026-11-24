"use client";

import type { ReactNode } from "react";

import { cn } from "@/lib/utils";
import { CATEGORIES } from "@/lib/categories";
import { useI18n } from "@/providers/i18n-provider";
import type { PostCategory } from "@/lib/types";

/**
 * Multi-select category filter. An empty `selected` set means "Tutti" (no
 * category filter); otherwise the feed shows posts in ANY selected category.
 */
export function CategoryPills({
  selected,
  onToggle,
  onClear,
  trailing,
}: {
  selected: Set<PostCategory>;
  onToggle: (category: PostCategory) => void;
  onClear: () => void;
  /** Extra pill(s) rendered inline after the categories (e.g. a Sondaggi toggle). */
  trailing?: ReactNode;
}) {
  const { t } = useI18n();

  const pillClass = (active: boolean) =>
    cn(
      "border px-3 py-1.5 font-mono text-xs transition-colors rounded-[var(--radius-pill)]",
      active
        ? "border-[var(--border)] bg-[var(--primary)] text-[var(--primary-fg)] retro-shadow-sm"
        : "border-[var(--border)] bg-[var(--surface)] text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--surface-2)]",
    );

  return (
    <div className="flex flex-wrap gap-2" role="group" aria-label={t("cat.filter")}>
      <button
        type="button"
        aria-pressed={selected.size === 0}
        onClick={onClear}
        className={pillClass(selected.size === 0)}
      >
        {t("cat.all")}
      </button>
      {CATEGORIES.map((c) => {
        const active = selected.has(c.slug);
        return (
          <button
            key={c.slug}
            type="button"
            aria-pressed={active}
            onClick={() => onToggle(c.slug)}
            className={pillClass(active)}
          >
            {t(`cat.${c.slug}`)}
          </button>
        );
      })}
      {trailing}
    </div>
  );
}
