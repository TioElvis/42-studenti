"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ChevronLeft, ChevronRight, Search } from "lucide-react";

import { Avatar } from "@/components/chrome/avatar";
import { SectionHeading } from "@/components/chrome/section-heading";
import { Window, WindowBar } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";
import { useI18n } from "@/providers/i18n-provider";
import type { StudentPage } from "@/lib/types";

const MIN = 2; // shortest query that filters the list

export function StudentSearch() {
  const { t } = useI18n();
  const router = useRouter();
  const [q, setQ] = React.useState("");
  const [page, setPage] = React.useState(1);
  const [data, setData] = React.useState<StudentPage | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [failed, setFailed] = React.useState(false);

  const query = q.trim().length >= MIN ? q.trim() : "";

  // A new query always starts from the first page.
  React.useEffect(() => {
    setPage(1);
  }, [query]);

  // The directory (everyone who uses the app), one page at a time; a 2+ char
  // query filters it. Debounced so typing doesn't fire a request per key.
  React.useEffect(() => {
    setLoading(true);
    setFailed(false);
    let active = true;
    const id = setTimeout(
      () => {
        api
          .studentsPage(query, page)
          .then((r) => {
            if (!active) return;
            setData(r);
            if (r.page !== page) setPage(r.page); // server clamped a stale page
          })
          .catch(() => {
            if (active) setFailed(true);
          })
          .finally(() => {
            if (active) setLoading(false);
          });
      },
      query ? 250 : 0,
    );
    return () => {
      active = false;
      clearTimeout(id);
    };
  }, [query, page]);

  function onKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    const query = q.trim();
    if (e.key === "Enter" && query) {
      router.push(`/u/${encodeURIComponent(query)}`);
    }
  }

  return (
    <section>
      <SectionHeading label={t("students.label")} desc={t("students.desc")} />

      <Window className="retro-shadow">
        <WindowBar title={t("students.bar")} />
        <div className="p-4">
          <div className="relative">
            <Search
              className="pointer-events-none absolute left-2 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--text-muted)]"
              aria-hidden
            />
            <Input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              onKeyDown={onKeyDown}
              placeholder={t("students.placeholder")}
              aria-label={t("students.placeholder")}
              className="pl-8"
              autoFocus
            />
          </div>
          <p className="mt-2 font-mono text-[11px] text-[var(--text-muted)]">{t("students.hint")}</p>

          <div className="mt-3">
            {failed ? (
              <p className="font-mono text-sm text-[var(--primary)]" role="alert">
                {t("students.error")}
              </p>
            ) : loading && !data ? (
              <div className="flex flex-col gap-2">
                <Skeleton className="h-12 w-full" />
                <Skeleton className="h-12 w-full" />
                <Skeleton className="h-12 w-full" />
              </div>
            ) : data && data.items.length === 0 ? (
              <p className="font-mono text-sm text-[var(--text-muted)]">
                {t("students.noResults")}
              </p>
            ) : (
              <ul
                className={cn("flex flex-col gap-2 transition-opacity", loading && "opacity-60")}
                aria-busy={loading}
              >
                {data?.items.map((u) => (
                  <li key={u.id}>
                    <Link
                      href={`/u/${u.login}`}
                      className="flex items-center gap-2.5 border border-[var(--border-subtle)] bg-[var(--surface-sunken)] p-2 transition-colors hover:bg-[var(--surface-2)] rounded-[var(--radius-inner)]"
                    >
                      <Avatar user={u} size={32} />
                      <span className="min-w-0">
                        <span className="block truncate font-mono text-sm font-bold">
                          @{u.login}
                        </span>
                        {u.display_name && (
                          <span className="block truncate text-xs text-[var(--text-muted)]">
                            {u.display_name}
                          </span>
                        )}
                      </span>
                    </Link>
                  </li>
                ))}
              </ul>
            )}

            {data && data.total > 0 && !failed && (
              <nav
                className="mt-4 flex flex-wrap items-center justify-between gap-2 border-t border-[var(--border-subtle)] pt-3 font-mono text-xs"
                aria-label={t("students.pagination")}
              >
                <span className="text-[var(--text-muted)]">
                  {t("students.total", { n: data.total })}
                </span>
                <span className="flex items-center gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={loading || data.page <= 1}
                    aria-label={t("students.prev")}
                  >
                    <ChevronLeft className="h-4 w-4" aria-hidden />
                  </Button>
                  <span aria-live="polite">
                    {t("students.pageOf", { page: data.page, pages: data.pages })}
                  </span>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setPage((p) => Math.min(data.pages, p + 1))}
                    disabled={loading || data.page >= data.pages}
                    aria-label={t("students.next")}
                  >
                    <ChevronRight className="h-4 w-4" aria-hidden />
                  </Button>
                </span>
              </nav>
            )}
          </div>
        </div>
      </Window>
    </section>
  );
}
