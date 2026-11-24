"use client";

import * as React from "react";
import { Bell } from "lucide-react";

import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { useI18n } from "@/providers/i18n-provider";
import { NotificationDialog } from "./notification-dialog";

const POLL_MS = 30_000;

/** Header bell: polls the unread count and shows a badge. Opens the dialog. */
export function NotificationBell() {
  const { t } = useI18n();
  const [unread, setUnread] = React.useState(0);
  const [open, setOpen] = React.useState(false);

  const refresh = React.useCallback(async () => {
    try {
      const res = await api.unreadNotifications();
      setUnread(res.unread);
    } catch {
      /* transient network/auth error — keep the last known count */
    }
  }, []);

  React.useEffect(() => {
    let active = true;
    const tick = () => {
      if (active && document.visibilityState === "visible") void refresh();
    };
    void refresh();
    const timer = setInterval(tick, POLL_MS);
    document.addEventListener("visibilitychange", tick);
    return () => {
      active = false;
      clearInterval(timer);
      document.removeEventListener("visibilitychange", tick);
    };
  }, [refresh]);

  // Re-sync when the dialog closes (any just-read state is reflected).
  const handleOpenChange = React.useCallback(
    (next: boolean) => {
      setOpen(next);
      if (!next) void refresh();
    },
    [refresh],
  );

  return (
    <>
      <span className="relative inline-flex">
        <Button
          variant="outline"
          size="icon"
          aria-label={t("notifications.trigger")}
          onClick={() => setOpen(true)}
        >
          <Bell className="h-4 w-4" />
        </Button>
        {unread > 0 && (
          <span
            aria-hidden
            className="pointer-events-none absolute -right-1.5 -top-1.5 min-w-[18px] border border-[var(--border)] bg-[var(--primary)] px-1 text-center font-mono text-[10px] font-bold leading-[16px] text-[var(--primary-fg)] rounded-[var(--radius-pill)]"
          >
            {unread > 99 ? "99+" : unread}
          </span>
        )}
      </span>

      <NotificationDialog
        open={open}
        onOpenChange={handleOpenChange}
        onUnreadCleared={() => setUnread(0)}
      />
    </>
  );
}
