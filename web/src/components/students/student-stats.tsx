"use client";

import * as React from "react";
import Link from "next/link";
import { Coins, Clock, Heart, Users } from "lucide-react";

import { Avatar } from "@/components/chrome/avatar";
import { Window, WindowBar } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { useI18n } from "@/providers/i18n-provider";
import type { StatRow, StudentStats } from "@/lib/types";

type Tab = "followers" | "daje" | "wallet" | "cluster";

const MEDALS = ["🥇", "🥈", "🥉"];

/** 12345 → "12.345" (locale-aware); seconds → "86h 20m". */
function fmt(tab: Tab, value: number, lang: string): string {
  if (tab === "cluster") {
    const h = Math.floor(value / 3600);
    const m = Math.floor((value % 3600) / 60);
    return h > 0 ? `${h}h ${String(m).padStart(2, "0")}m` : `${m}m`;
  }
  const n = value.toLocaleString(lang === "en" ? "en-GB" : "it-IT");
  return tab === "wallet" ? `${n} ₳` : n;
}

/** "Classifiche": top 10 students by followers, Daje, wallet and cluster time. */
export function StudentStats() {
  const { t, lang } = useI18n();
  const [tab, setTab] = React.useState<Tab>("followers");
  const [data, setData] = React.useState<StudentStats | null>(null);
  const [failed, setFailed] = React.useState(false);

  React.useEffect(() => {
    let active = true;
    api
      .studentStats()
      .then((d) => active && setData(d))
      .catch(() => active && setFailed(true));
    return () => {
      active = false;
    };
  }, []);

  // The 42-based boards are empty until the first background snapshot is ready:
  // poll gently so they fill in without a reload.
  React.useEffect(() => {
    if (!data || data.intra_ready) return;
    const id = setTimeout(() => {
      api.studentStats().then(setData).catch(() => undefined);
    }, 8000);
    return () => clearTimeout(id);
  }, [data]);

  const TABS: { id: Tab; icon: typeof Users; label: string }[] = [
    { id: "followers", icon: Users, label: t("stats.followers") },
    { id: "daje", icon: Heart, label: t("stats.daje") },
    { id: "wallet", icon: Coins, label: t("stats.wallet") },
    { id: "cluster", icon: Clock, label: t("stats.cluster") },
  ];

  const rows: StatRow[] = data ? data[tab] : [];
  const needs42 = tab === "wallet" || tab === "cluster";
  const preparing = needs42 && data !== null && !data.intra_ready;

  const updated =
    needs42 && data?.intra_updated_at
      ? new Date(data.intra_updated_at).toLocaleTimeString(lang === "en" ? "en-GB" : "it-IT", {
          hour: "2-digit",
          minute: "2-digit",
        })
      : null;

  return (
    <Window className="retro-shadow mb-4">
      <WindowBar title={t("stats.bar")} />
      <div className="p-4">
        <div className="flex flex-wrap gap-2" role="tablist" aria-label={t("stats.title")}>
          {TABS.map(({ id, icon: Icon, label }) => (
            <button
              key={id}
              type="button"
              role="tab"
              aria-selected={tab === id}
              onClick={() => setTab(id)}
              className={cn(
                "inline-flex items-center gap-1.5 border px-2.5 py-1 font-mono text-xs transition-colors rounded-[var(--radius-button)]",
                tab === id
                  ? "border-[var(--ring)] bg-[var(--surface-2)]"
                  : "border-[var(--border)] bg-[var(--surface)] text-[var(--text-muted)] hover:text-[var(--text)]",
              )}
            >
              <Icon className="h-3.5 w-3.5" aria-hidden /> {label}
            </button>
          ))}
        </div>

        <p className="mt-2 font-mono text-[11px] text-[var(--text-muted)]">
          {t(`stats.hint.${tab}`, { days: data?.cluster_days ?? 30 })}
        </p>

        <div className="mt-3" role="tabpanel">
          {failed ? (
            <p className="font-mono text-sm text-[var(--primary)]" role="alert">
              {t("stats.error")}
            </p>
          ) : data === null ? (
            <div className="flex flex-col gap-2">
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
            </div>
          ) : preparing ? (
            <p className="font-mono text-sm text-[var(--text-muted)]">
              {t("stats.preparing")}
              <span className="cursor-blink">_</span>
            </p>
          ) : rows.length === 0 ? (
            <p className="font-mono text-sm text-[var(--text-muted)]">{t("stats.empty")}</p>
          ) : (
            <ol className="flex flex-col gap-1.5">
              {rows.map((r, i) => (
                <li key={r.login}>
                  <Link
                    href={`/u/${r.login}`}
                    className="flex items-center gap-2.5 border border-[var(--border-subtle)] bg-[var(--surface-sunken)] p-2 transition-colors hover:bg-[var(--surface-2)] rounded-[var(--radius-inner)]"
                  >
                    <span className="w-7 shrink-0 text-center font-mono text-sm" aria-hidden>
                      {MEDALS[i] ?? `${i + 1}.`}
                    </span>
                    <Avatar user={r} size={28} />
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm font-bold">
                        {r.display_name ?? r.login}
                      </span>
                      <span className="block truncate font-mono text-xs text-[var(--text-muted)]">
                        @{r.login}
                      </span>
                    </span>
                    <span className="shrink-0 font-mono text-sm font-bold tabular-nums">
                      {fmt(tab, r.value, lang)}
                    </span>
                  </Link>
                </li>
              ))}
            </ol>
          )}
        </div>

        {updated && !preparing && (
          <p className="mt-3 font-mono text-[11px] text-[var(--text-muted)]">
            {t("stats.updated", { time: updated })}
          </p>
        )}
      </div>
    </Window>
  );
}
