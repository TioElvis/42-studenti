"use client";

import * as React from "react";
import { ArrowLeft } from "lucide-react";
import { useRouter } from "next/navigation";

import { Avatar } from "@/components/chrome/avatar";
import { Window, WindowBar } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { api, ApiError } from "@/lib/api";
import { fullDate } from "@/lib/time";
import { useI18n } from "@/providers/i18n-provider";
import type { Profile, ProjectInfo } from "@/lib/types";

function Stat({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="border border-[var(--border-subtle)] bg-[var(--surface-sunken)] p-3 text-center">
      <div className="font-display text-2xl font-bold tabular-nums">{value}</div>
      <div className="mt-0.5 font-mono text-[11px] uppercase tracking-wide text-[var(--text-muted)]">
        {label}
      </div>
    </div>
  );
}

function projectStatus(p: ProjectInfo, t: (k: string) => string): { text: string; cls: string } {
  if (p.status === "finished") {
    return {
      text: `${p.mark ?? "—"} ${p.validated ? "✓" : "✗"}`,
      cls: p.validated === false ? "text-[var(--primary)]" : "",
    };
  }
  const label =
    p.status === "in_progress"
      ? t("profile.statusInProgress")
      : p.status === "waiting_for_correction"
        ? t("profile.statusWaiting")
        : p.status === "searching_a_group"
          ? t("profile.statusGroup")
          : p.status;
  return { text: label, cls: "text-[var(--text-muted)]" };
}

export function ProfileView({ login }: { login: string }) {
  const { t, lang } = useI18n();
  const router = useRouter();
  const [profile, setProfile] = React.useState<Profile | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    let cancelled = false;
    setProfile(null);
    setError(null);
    api
      .getProfile(login)
      .then((p) => {
        if (!cancelled) setProfile(p);
      })
      .catch((e) => {
        if (cancelled) return;
        setError(
          e instanceof ApiError && e.status === 404
            ? t("profile.notFound")
            : e instanceof ApiError
              ? e.message
              : t("profile.loadError"),
        );
      });
    return () => {
      cancelled = true;
    };
  }, [login, t]);

  return (
    <section className="flex flex-col gap-4">
      <button
        type="button"
        onClick={() => router.back()}
        className="inline-flex w-fit items-center gap-1 font-mono text-xs text-[var(--text-muted)] hover:text-[var(--text)]"
      >
        <ArrowLeft className="h-3.5 w-3.5" aria-hidden /> {t("profile.back")}
      </button>

      {error ? (
        <div className="window retro-shadow p-8 text-center font-mono text-sm text-[var(--primary)]">
          {error}
        </div>
      ) : profile === null ? (
        <Skeleton className="h-64 w-full" />
      ) : (
        <>
          <Window className="retro-shadow-lg">
            <WindowBar title={t("profile.bar")} />
            <div className="flex flex-col items-center gap-4 p-6 text-center sm:flex-row sm:text-left">
              <Avatar user={profile} size={88} />
              <div className="min-w-0">
                <h1 className="font-display text-2xl font-bold">
                  {profile.display_name ?? profile.login}
                </h1>
                <div className="font-mono text-sm text-[var(--text-muted)]">@{profile.login}</div>
                <div className="mt-2 flex flex-wrap items-center justify-center gap-2 font-mono text-[11px] text-[var(--text-muted)] sm:justify-start">
                  {profile.is_me && (
                    <span className="border border-[var(--primary)] px-1.5 py-0.5 text-[var(--primary)]">
                      {t("profile.me")}
                    </span>
                  )}
                  {profile.campus && <span>{profile.campus}</span>}
                  {profile.intra.joined && (
                    <span>
                      {t("profile.memberSince")} {fullDate(profile.intra.joined, lang)}
                    </span>
                  )}
                </div>
              </div>
            </div>
          </Window>

          <Window className="retro-shadow">
            <WindowBar title={t("profile.intraTitle")} />
            <div className="grid grid-cols-2 gap-2 p-4 sm:grid-cols-3">
              {profile.intra.level != null && (
                <Stat label={t("profile.level")} value={profile.intra.level.toFixed(2)} />
              )}
              {profile.intra.grade && (
                <Stat label={t("profile.grade")} value={profile.intra.grade} />
              )}
              {profile.intra.correction_point != null && (
                <Stat label={t("profile.points")} value={profile.intra.correction_point} />
              )}
              {profile.intra.wallet != null && (
                <Stat label={t("profile.wallet")} value={`${profile.intra.wallet} ₳`} />
              )}
              {profile.intra.pool && <Stat label={t("profile.pool")} value={profile.intra.pool} />}
              {profile.intra.location && (
                <Stat label={t("profile.location")} value={profile.intra.location} />
              )}
            </div>
          </Window>

          {profile.intra.projects.length > 0 && (
            <Window className="retro-shadow">
              <WindowBar title={t("profile.projectsTitle")} />
              <ul className="flex flex-col gap-1.5 p-3">
                {profile.intra.projects.map((p) => {
                  const s = projectStatus(p, t);
                  return (
                    <li
                      key={p.name}
                      className="flex items-center justify-between gap-2 border border-[var(--border-subtle)] bg-[var(--surface-sunken)] px-3 py-2 font-mono text-sm"
                    >
                      <span className="min-w-0 truncate font-bold">{p.name}</span>
                      <span className={cn("shrink-0 text-xs", s.cls)}>{s.text}</span>
                    </li>
                  );
                })}
              </ul>
            </Window>
          )}

          {profile.intra.achievements.length > 0 && (
            <Window className="retro-shadow">
              <WindowBar title={t("profile.achievementsTitle")}>
                <span>{profile.intra.achievements.length}</span>
              </WindowBar>
              <div className="flex flex-wrap gap-1.5 p-3">
                {profile.intra.achievements.map((a) => (
                  <span
                    key={a}
                    className="border border-[var(--border-subtle)] bg-[var(--surface-2)] px-2 py-0.5 font-mono text-[11px]"
                  >
                    {a}
                  </span>
                ))}
              </div>
            </Window>
          )}

          <Window className="retro-shadow">
            <WindowBar title={t("profile.activityTitle")} />
            <div className="grid grid-cols-2 gap-2 p-4 sm:grid-cols-5">
              <Stat label={t("profile.posts")} value={profile.activity.posts} />
              <Stat label={t("profile.daje")} value={profile.activity.daje_received} />
              <Stat label={t("profile.comments")} value={profile.activity.comments} />
              <Stat label={t("profile.rsvps")} value={profile.activity.rsvps} />
              <Stat label={t("profile.logins")} value={profile.activity.logins} />
            </div>
          </Window>
        </>
      )}
    </section>
  );
}
