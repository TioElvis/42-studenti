"use client";

import * as React from "react";
import { Check } from "lucide-react";

import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { useI18n } from "@/providers/i18n-provider";
import type { NotificationSettings, PostNotify } from "@/lib/types";

const POST_OPTIONS: { id: PostNotify; key: string }[] = [
  { id: "followed", key: "notifications.postsFollowed" },
  { id: "all", key: "notifications.postsAll" },
  { id: "off", key: "notifications.postsOff" },
];

function Toggle({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className="mt-2.5 flex w-full items-center justify-between gap-3 border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-left transition-colors hover:bg-[var(--surface-2)] rounded-[var(--radius-button)]"
    >
      <span className="font-mono text-sm">{label}</span>
      <span
        aria-hidden
        className={cn(
          "relative inline-flex h-5 w-9 shrink-0 items-center border border-[var(--border)] transition-colors rounded-[var(--radius-pill)]",
          checked ? "bg-[var(--primary)]" : "bg-[var(--surface-sunken)]",
        )}
      >
        <span
          className={cn(
            "block h-3.5 w-3.5 border border-[var(--border)] bg-[var(--surface)] transition-transform rounded-[var(--radius-pill)]",
            checked ? "translate-x-4" : "translate-x-0.5",
          )}
        />
      </span>
    </button>
  );
}

/** Notification preferences, fetched on mount (mounted only when the modal opens). */
export function NotificationSettingsSection() {
  const { t } = useI18n();
  const [settings, setSettings] = React.useState<NotificationSettings | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    let active = true;
    api
      .getNotificationSettings()
      .then((s) => {
        if (active) setSettings(s);
      })
      .catch(() => {
        if (active) setError(t("notifications.loadError"));
      });
    return () => {
      active = false;
    };
  }, [t]);

  async function patch(partial: Partial<NotificationSettings>) {
    if (!settings) return;
    const prev = settings;
    setSettings({ ...settings, ...partial });
    setError(null);
    try {
      const next = await api.updateNotificationSettings(partial);
      setSettings(next);
    } catch {
      setSettings(prev);
      setError(t("notifications.saveError"));
    }
  }

  if (!settings) {
    return error ? (
      <p className="text-sm text-[var(--primary)]">{error}</p>
    ) : (
      <div className="flex flex-col gap-2">
        <Skeleton className="h-9 w-full" />
        <Skeleton className="h-9 w-full" />
      </div>
    );
  }

  return (
    <div>
      <p className="mb-2 font-mono text-xs font-bold uppercase tracking-wide text-[var(--text-muted)]">
        {t("notifications.postsLabel")}
      </p>
      <div className="flex gap-2">
        {POST_OPTIONS.map((o) => {
          const active = settings.notify_posts === o.id;
          return (
            <button
              key={o.id}
              type="button"
              aria-pressed={active}
              onClick={() => patch({ notify_posts: o.id })}
              className={cn(
                "flex flex-1 items-center justify-center gap-1.5 border px-2 py-2 text-center font-mono text-xs transition-colors rounded-[var(--radius-button)]",
                active
                  ? "border-[var(--ring)] bg-[var(--surface-2)] font-bold"
                  : "border-[var(--border)] bg-[var(--surface)] text-[var(--text-muted)] hover:text-[var(--text)]",
              )}
            >
              {active && <Check className="h-3.5 w-3.5 shrink-0 text-[var(--ring)]" aria-hidden />}
              {t(o.key)}
            </button>
          );
        })}
      </div>

      <Toggle
        label={t("notifications.commentsLabel")}
        checked={settings.notify_comments}
        onChange={(v) => patch({ notify_comments: v })}
      />
      <Toggle
        label={t("notifications.followsLabel")}
        checked={settings.notify_follows}
        onChange={(v) => patch({ notify_follows: v })}
      />

      {error && <p className="mt-2 text-xs text-[var(--primary)]">{error}</p>}
    </div>
  );
}
