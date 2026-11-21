"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import { categoryMeta } from "@/lib/categories";
import { useI18n } from "@/providers/i18n-provider";
import type { PostCategory } from "@/lib/types";

/** A category badge whose colors come from theme-scoped CSS vars. */
export function CategoryBadge({
  category,
  terminal = false,
  className,
}: {
  category: PostCategory;
  terminal?: boolean;
  className?: string;
}) {
  const { t } = useI18n();
  const meta = categoryMeta(category);
  return (
    <span className={cn("cat-badge", meta.colorClass, className)}>
      {terminal ? `[${meta.terminal}]` : t(`cat.${category}`)}
    </span>
  );
}
