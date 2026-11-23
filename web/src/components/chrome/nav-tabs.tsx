"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

import { cn } from "@/lib/utils";
import { useI18n } from "@/providers/i18n-provider";

const TABS = [
  { href: "/", key: "nav.bacheca" },
  { href: "/comunita", key: "nav.comunita" },
  { href: "/eventi", key: "nav.eventi" },
  { href: "/studenti", key: "nav.studenti" },
  { href: "/club", key: "nav.club" },
  { href: "/staff", key: "nav.staff" },
  { href: "/materiale", key: "nav.materiale" },
  { href: "/archivio", key: "nav.archivio" },
] as const;

export function NavTabs() {
  const pathname = usePathname();
  const router = useRouter();
  const { t } = useI18n();
  const current = TABS.find((t) => t.href === pathname)?.href ?? "/";

  return (
    <>
      {/* Mobile: a dropdown to switch section — avoids horizontal overflow. */}
      <div className="sm:hidden">
        <label htmlFor="nav-select" className="sr-only">
          {t("nav.section")}
        </label>
        <select
          id="nav-select"
          value={current}
          onChange={(e) => router.push(e.target.value)}
          className="w-full border border-[var(--border)] bg-[var(--surface)] px-3 py-2 font-mono text-sm text-[var(--text)] retro-shadow-sm focus-visible:outline-2 focus-visible:outline-offset-2"
        >
          {TABS.map((tab) => (
            <option key={tab.href} value={tab.href}>
              {t(tab.key)}
            </option>
          ))}
        </select>
      </div>

      {/* sm and up: the retro tab row (wraps rather than overflowing). */}
      <nav className="hidden flex-wrap items-center gap-1 sm:flex" aria-label="Sezioni">
        {TABS.map((tab) => {
          const active = pathname === tab.href;
          return (
            <Link
              key={tab.href}
              href={tab.href}
              aria-current={active ? "page" : undefined}
              className={cn(
                "border px-3.5 py-1.5 font-mono text-sm transition-colors",
                active
                  ? "border-[var(--border)] bg-[var(--primary)] text-[var(--primary-fg)] retro-shadow-sm"
                  : "border-transparent text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--surface-2)]",
              )}
            >
              {t(tab.key)}
            </Link>
          );
        })}
      </nav>
    </>
  );
}
