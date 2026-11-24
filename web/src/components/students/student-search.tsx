"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Search } from "lucide-react";

import { Avatar } from "@/components/chrome/avatar";
import { SectionHeading } from "@/components/chrome/section-heading";
import { Window, WindowBar } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { useI18n } from "@/providers/i18n-provider";
import type { UserPublic } from "@/lib/types";

const MIN = 2;

export function StudentSearch() {
  const { t } = useI18n();
  const router = useRouter();
  const [q, setQ] = React.useState("");
  const [results, setResults] = React.useState<UserPublic[] | null>(null);
  const [loading, setLoading] = React.useState(false);

  // Debounced autocomplete over app students.
  React.useEffect(() => {
    const query = q.trim();
    if (query.length < MIN) {
      setResults(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    let active = true;
    const id = setTimeout(() => {
      api
        .searchStudents(query)
        .then((r) => {
          if (active) {
            setResults(r);
            setLoading(false);
          }
        })
        .catch(() => {
          if (active) {
            setResults([]);
            setLoading(false);
          }
        });
    }, 250);
    return () => {
      active = false;
      clearTimeout(id);
    };
  }, [q]);

  function onKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    const query = q.trim();
    if (e.key === "Enter" && query) {
      router.push(`/u/${encodeURIComponent(query)}`);
    }
  }

  const tooShort = q.trim().length < MIN;

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
            {tooShort ? (
              <p className="font-mono text-sm text-[var(--text-muted)]">{t("students.minChars")}</p>
            ) : loading ? (
              <div className="flex flex-col gap-2">
                <Skeleton className="h-12 w-full" />
                <Skeleton className="h-12 w-full" />
              </div>
            ) : results && results.length === 0 ? (
              <p className="font-mono text-sm text-[var(--text-muted)]">
                {t("students.noResults")}
              </p>
            ) : (
              <ul className="flex flex-col gap-2">
                {results?.map((u) => (
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
          </div>
        </div>
      </Window>
    </section>
  );
}
