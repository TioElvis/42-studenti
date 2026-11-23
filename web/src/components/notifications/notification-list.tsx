"use client";

import * as React from "react";
import Link from "next/link";

import { Avatar } from "@/components/chrome/avatar";
import { SectionHeading } from "@/components/chrome/section-heading";
import { Button } from "@/components/ui/button";
import { Window, WindowBar } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { relativeTime } from "@/lib/time";
import { cn } from "@/lib/utils";
import { useI18n } from "@/providers/i18n-provider";
import type { AppNotification, NotificationKind } from "@/lib/types";

const TEXT_KEY: Record<NotificationKind, string> = {
  post: "notifications.textPost",
  comment: "notifications.textComment",
  reply: "notifications.textReply",
  follow: "notifications.textFollow",
};

function hrefFor(n: AppNotification): string {
  if (n.type === "follow") return `/u/${n.actor.login}`;
  return n.post_id != null ? `/?post=${n.post_id}` : "/";
}

export function NotificationList() {
  const { t, lang } = useI18n();
  const [items, setItems] = React.useState<AppNotification[] | null>(null);
  const [cursor, setCursor] = React.useState<number | null>(null);
  const [loadingMore, setLoadingMore] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  // First page + clear the unread badge once we've shown them.
  React.useEffect(() => {
    let active = true;
    api
      .listNotifications()
      .then((page) => {
        if (!active) return;
        setItems(page.items);
        setCursor(page.next_cursor);
        if (page.unread > 0) void api.markNotificationsRead().catch(() => {});
      })
      .catch(() => {
        if (active) setError(t("notifications.loadError"));
      });
    return () => {
      active = false;
    };
  }, [t]);

  async function loadMore() {
    if (cursor == null || loadingMore) return;
    setLoadingMore(true);
    try {
      const page = await api.listNotifications(cursor);
      setItems((prev) => [...(prev ?? []), ...page.items]);
      setCursor(page.next_cursor);
    } catch {
      setError(t("notifications.loadError"));
    } finally {
      setLoadingMore(false);
    }
  }

  return (
    <section>
      <SectionHeading label={t("notifications.title")} desc={t("notifications.settingsIntro")} />

      <Window className="retro-shadow">
        <WindowBar title={t("notifications.bar")} />
        <div className="p-4">
          {error ? (
            <p className="font-mono text-sm text-[var(--primary)]">{error}</p>
          ) : items === null ? (
            <div className="flex flex-col gap-2">
              <Skeleton className="h-14 w-full" />
              <Skeleton className="h-14 w-full" />
              <Skeleton className="h-14 w-full" />
            </div>
          ) : items.length === 0 ? (
            <p className="font-mono text-sm text-[var(--text-muted)]">{t("notifications.empty")}</p>
          ) : (
            <>
              <ul className="flex flex-col gap-2">
                {items.map((n) => (
                  <li key={n.id}>
                    <Link
                      href={hrefFor(n)}
                      className={cn(
                        "flex items-center gap-2.5 border border-[var(--border-subtle)] p-2.5 transition-colors hover:bg-[var(--surface-2)]",
                        n.is_read
                          ? "bg-[var(--surface-sunken)]"
                          : "border-l-2 border-l-[var(--primary)] bg-[var(--surface)]",
                      )}
                    >
                      <Avatar user={n.actor} size={34} />
                      <span className="min-w-0 flex-1">
                        <span className="block text-sm">
                          {t(TEXT_KEY[n.type], { actor: `@${n.actor.login}` })}
                        </span>
                        <span className="block font-mono text-[11px] text-[var(--text-muted)]">
                          {relativeTime(n.created_at, lang)}
                        </span>
                      </span>
                      {!n.is_read && (
                        <span
                          aria-hidden
                          className="h-2 w-2 shrink-0 rounded-full bg-[var(--primary)]"
                        />
                      )}
                    </Link>
                  </li>
                ))}
              </ul>

              {cursor != null && (
                <div className="mt-3 flex justify-center">
                  <Button variant="outline" size="sm" onClick={loadMore} disabled={loadingMore}>
                    {t("notifications.loadMore")}
                  </Button>
                </div>
              )}
            </>
          )}
        </div>
      </Window>
    </section>
  );
}
