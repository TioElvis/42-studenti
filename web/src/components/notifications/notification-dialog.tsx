"use client";

import * as React from "react";
import { ArrowLeft, Settings2 } from "lucide-react";

import { Dialog, DialogContent } from "@/components/ui/dialog";
import { cn } from "@/lib/utils";
import { useI18n } from "@/providers/i18n-provider";
import type { NotificationFilter } from "@/lib/types";
import { NotificationList } from "./notification-list";
import { NotificationSettingsSection } from "./notification-settings";

const TABS: { id: NotificationFilter; key: string }[] = [
  { id: "all", key: "notifications.filterAll" },
  { id: "posts", key: "notifications.filterPosts" },
  { id: "comments", key: "notifications.filterComments" },
  { id: "follows", key: "notifications.filterFollows" },
];

/** Interactive notifications panel opened from the header bell. Toggles between
 * the notification list and the notification settings. */
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
  const [view, setView] = React.useState<"list" | "settings">("list");

  // Start each visit on the list, "All" tab.
  React.useEffect(() => {
    if (open) {
      setFilter("all");
      setView("list");
    }
  }, [open]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent title={t("notifications.title")} barTitle={t("notifications.bar")}>
        <div className="mb-3 flex items-center justify-between gap-2">
          {view === "list" ? (
            <div className="flex flex-wrap gap-1.5">
              {TABS.map((tab) => {
                const active = filter === tab.id;
                return (
                  <button
                    key={tab.id}
                    type="button"
                    aria-pressed={active}
                    onClick={() => setFilter(tab.id)}
                    className={cn(
                      "border px-3 py-1.5 font-mono text-xs transition-colors rounded-[var(--radius-pill)]",
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
          ) : (
            <button
              type="button"
              onClick={() => setView("list")}
              className="inline-flex items-center gap-1.5 border border-[var(--border)] bg-[var(--surface)] px-3 py-1.5 font-mono text-xs transition-colors hover:bg-[var(--surface-2)] rounded-[var(--radius-button)]"
            >
              <ArrowLeft className="h-3.5 w-3.5" aria-hidden />
              {t("notifications.backToList")}
            </button>
          )}

          {view === "list" && (
            <button
              type="button"
              aria-label={t("notifications.settingsToggle")}
              onClick={() => setView("settings")}
              className="inline-flex h-8 w-8 shrink-0 items-center justify-center border border-[var(--border)] bg-[var(--surface)] transition-colors hover:bg-[var(--surface-2)] rounded-[var(--radius-button)]"
            >
              <Settings2 className="h-4 w-4" />
            </button>
          )}
        </div>

        {view === "settings" ? (
          <>
            <p className="mb-3 text-sm text-[var(--text-muted)]">
              {t("notifications.settingsIntro")}
            </p>
            <NotificationSettingsSection />
          </>
        ) : (
          open && (
            <NotificationList
              filter={filter}
              onUnreadCleared={onUnreadCleared}
              onItemClick={() => onOpenChange(false)}
            />
          )
        )}
      </DialogContent>
    </Dialog>
  );
}
