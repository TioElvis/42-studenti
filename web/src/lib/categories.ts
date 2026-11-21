import type { PostCategory } from "./types";

export interface CategoryMeta {
  slug: PostCategory;
  /** Terminal-style label for the hacker theme badge, e.g. [STUDIO]. */
  terminal: string;
  /** CSS class selecting the per-category color vars (see globals.css). */
  colorClass: string;
}

// Human labels/hints are translated in src/lib/messages.ts (cat.* / catHint.*).
export const CATEGORIES: CategoryMeta[] = [
  { slug: "studio", terminal: "STUDIO", colorClass: "cat-studio" },
  { slug: "cerco_team", terminal: "CERCO_TEAM", colorClass: "cat-cerco_team" },
  { slug: "evento_casuale", terminal: "EVENTO", colorClass: "cat-evento_casuale" },
  { slug: "vita_romana", terminal: "VITA_ROMANA", colorClass: "cat-vita_romana" },
  { slug: "mercatino", terminal: "MERCATINO", colorClass: "cat-mercatino" },
  { slug: "off_topic", terminal: "OFF_TOPIC", colorClass: "cat-off_topic" },
];

const BY_SLUG = new Map<PostCategory, CategoryMeta>(CATEGORIES.map((c) => [c.slug, c]));

export function categoryMeta(slug: PostCategory): CategoryMeta {
  return BY_SLUG.get(slug) ?? CATEGORIES[0]!;
}
