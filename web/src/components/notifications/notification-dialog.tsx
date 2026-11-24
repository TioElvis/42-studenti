"use client";

import * as React from "react";

import { Dialog, DialogContent } from "@/components/ui/dialog";
import { cn } from "@/lib/utils";
import { useI18n } from "@/providers/i18n-provider";
import type { NotificationFilter } from "@/lib/types";
import { NotificationList } from "./notification-list";

const TABS: { id: NotificationFilter; key: string }[] = [
  { id: "all", key: "notifications.filterAll" },
  { id: "posts", key: "notifications.filterPosts" },
  { id: "comments", key: "notifications.filterComments" },
  { id: "follows", key: "notifications.filterFollows" },
];

/** Interactive notifications panel opened from the header bell. */
export function NotificationDialog({
  open,
  onOpenChange,
  onUnreadCleared,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onUnreadCleared: () => void;
}) {
  const { t } = useI18n();
  const [filter, setFilter] = React.useState<NotificationFilter>("all");

  // Start each visit on the "All" tab.
  React.useEffect(() => {
    if (open) setFilter("all");
  }, [open]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent title={t("notifications.title")} barTitle={t("notifications.bar")}>
        <div className="mb-3 flex flex-wrap gap-1.5">
          {TABS.map((tab) => {
            const active = filter === tab.id;
            return (
              <button
                key={tab.id}
                type="button"
                aria-pressed={active}
                onClick={() => setFilter(tab.id)}
                className={cn(
                  "border px-3 py-1.5 font-mono text-xs transition-colors",
                  active
                    ? "border-[var(--border)] bg-[var(--primary)] text-[var(--primary-fg)] retro-shadow-sm"
                    : "border-[var(--border)] bg-[var(--surface)] text-[var(--text-muted)] hover:text-[var(--text)]",
                )}
              >
                {t(tab.key)}
              </button>
            );
          })}
        </div>

        {open && (
          <NotificationList
            filter={filter}
            onUnreadCleared={onUnreadCleared}
            onItemClick={() => onOpenChange(false)}
          />
        )}
      </DialogContent>
    </Dialog>
  );
}
