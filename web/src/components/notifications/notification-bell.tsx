"use client";

import * as React from "react";
import Link from "next/link";
import { Bell } from "lucide-react";

import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { useI18n } from "@/providers/i18n-provider";

const POLL_MS = 30_000;

/** Header bell: polls the unread count and shows a badge. Links to /notifiche. */
export function NotificationBell() {
  const { t } = useI18n();
  const [unread, setUnread] = React.useState(0);

  React.useEffect(() => {
    let active = true;
    async function tick() {
      try {
        const res = await api.unreadNotifications();
        if (active) setUnread(res.unread);
      } catch {
        /* transient network/auth error — keep the last known count */
      }
    }
    void tick();
    const timer = setInterval(() => {
      if (document.visibilityState === "visible") void tick();
    }, POLL_MS);
    const onVisible = () => {
      if (document.visibilityState === "visible") void tick();
    };
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      active = false;
      clearInterval(timer);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, []);

  return (
    <span className="relative inline-flex">
      <Button asChild variant="outline" size="icon" aria-label={t("notifications.trigger")}>
        <Link href="/notifiche">
          <Bell className="h-4 w-4" />
        </Link>
      </Button>
      {unread > 0 && (
        <span
          aria-hidden
          className="pointer-events-none absolute -right-1.5 -top-1.5 min-w-[18px] border border-[var(--border)] bg-[var(--primary)] px-1 text-center font-mono text-[10px] font-bold leading-[16px] text-[var(--primary-fg)]"
        >
          {unread > 99 ? "99+" : unread}
        </span>
      )}
    </span>
  );
}
