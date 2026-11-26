"use client";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useI18n } from "@/providers/i18n-provider";
import { useBrowserPush } from "./use-browser-push";

/** Shows whether browser notifications are on for this device, with a button to
 * turn them on or off. Hidden where they can't be used at all. */
export function PushStatusBadge() {
  const { t } = useI18n();
  const { available, supported, blocked, enabled, busy, failed, toggle } = useBrowserPush();

  if (!available || !supported) return null;

  const on = enabled && !blocked;
  const status = blocked
    ? "notifications.pushStatusBlocked"
    : on
      ? "notifications.pushStatusOn"
      : "notifications.pushStatusOff";

  return (
    <div className="mb-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span
          role="status"
          className={cn(
            "inline-flex items-center gap-1.5 border px-2.5 py-1 font-mono text-xs rounded-[var(--radius-pill)]",
            on
              ? "border-[var(--ring)] bg-[var(--surface-2)] font-bold"
              : "border-[var(--border)] bg-[var(--surface-sunken)] text-[var(--text-muted)]",
          )}
        >
          <span
            aria-hidden
            className={cn(
              "h-2 w-2 shrink-0 rounded-full",
              on ? "bg-[var(--ring)]" : "border border-[var(--text-muted)]",
            )}
          />
          {t(status)}
        </span>
        {!blocked && (
          <Button variant="outline" size="sm" disabled={busy} onClick={() => toggle(!enabled)}>
            {t(enabled ? "notifications.pushDisable" : "notifications.pushEnable")}
          </Button>
        )}
      </div>
      {blocked && (
        <p className="mt-1.5 text-xs text-[var(--text-muted)]">{t("notifications.pushBlocked")}</p>
      )}
      {failed && (
        <p className="mt-1.5 text-xs text-[var(--primary)]">{t("notifications.pushError")}</p>
      )}
    </div>
  );
}
