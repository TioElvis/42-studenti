import type { PostCategory } from "./types";

export interface CategoryMeta {
  slug: PostCategory;
  /** CSS class selecting the per-category color vars (see globals.css). */
  colorClass: string;
}

// Human labels/hints are translated in src/lib/messages.ts (cat.* / catHint.*).
export const CATEGORIES: CategoryMeta[] = [
  { slug: "studio", colorClass: "cat-studio" },
  { slug: "cerco_team", colorClass: "cat-cerco_team" },
  { slug: "evento_casuale", colorClass: "cat-evento_casuale" },
  { slug: "mercatino", colorClass: "cat-mercatino" },
  { slug: "off_topic", colorClass: "cat-off_topic" },
];

const BY_SLUG = new Map<PostCategory, CategoryMeta>(CATEGORIES.map((c) => [c.slug, c]));

export function categoryMeta(slug: PostCategory): CategoryMeta {
  return BY_SLUG.get(slug) ?? CATEGORIES[0]!;
}
