"use client";

import * as React from "react";
import Link from "next/link";
import { ChevronDown, ChevronUp, Users } from "lucide-react";

import { Avatar } from "@/components/chrome/avatar";
import { Skeleton } from "@/components/ui/skeleton";
import { api, ApiError } from "@/lib/api";
import { useI18n } from "@/providers/i18n-provider";
import type { EventAttendee } from "@/lib/types";

/** "Chi c'è" list for an event: names come straight from the 42 API. Loaded
 * lazily (only once opened) so browsing events costs no extra 42 calls. */
export function EventAttendees({
  eventId,
  refreshKey,
}: {
  eventId: number;
  /** Changes when the viewer (un)registers, so an open list reloads. */
  refreshKey: number;
}) {
  const { t } = useI18n();
  const [open, setOpen] = React.useState(false);
  const [people, setPeople] = React.useState<EventAttendee[] | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  // A different event → collapse and forget the previous list.
  React.useEffect(() => {
    setOpen(false);
    setPeople(null);
    setError(null);
  }, [eventId]);

  React.useEffect(() => {
    if (!open) return;
    let cancelled = false;
    setError(null);
    api
      .eventAttendees(eventId)
      .then((p) => {
        if (!cancelled) setPeople(p);
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof ApiError ? e.message : t("eventDetail.attendeesError"));
      });
    return () => {
      cancelled = true;
    };
  }, [open, eventId, refreshKey, t]);

  const Chevron = open ? ChevronUp : ChevronDown;

  return (
    <div className="border-t border-[var(--border-subtle)] pt-3">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="flex w-full items-center justify-between gap-2 font-mono text-sm hover:text-[var(--primary)]"
      >
        <span className="flex items-center gap-2">
          <Users className="h-4 w-4" aria-hidden />
          {open ? t("eventDetail.hideAttendees") : t("eventDetail.showAttendees")}
        </span>
        <Chevron className="h-4 w-4" aria-hidden />
      </button>

      {open && (
        <div className="mt-3">
          {error && (
            <p className="font-mono text-xs text-[var(--primary)]" role="alert">
              {error}
            </p>
          )}
          {!error && people === null && (
            <div className="flex flex-col gap-2">
              <Skeleton className="h-9 w-full" />
              <Skeleton className="h-9 w-full" />
            </div>
          )}
          {people && people.length === 0 && (
            <p className="font-mono text-xs text-[var(--text-muted)]">
              {t("eventDetail.attendeesEmpty")}
            </p>
          )}
          {people && people.length > 0 && (
            <ul className="flex max-h-64 flex-col gap-1.5 overflow-y-auto pr-1">
              {people.map((p) => (
                <li key={p.login}>
                  <Link
                    href={`/u/${p.login}`}
                    className="flex items-center gap-2.5 border border-[var(--border-subtle)] bg-[var(--surface-sunken)] p-2 transition-colors hover:bg-[var(--surface-2)] rounded-[var(--radius-inner)]"
                  >
                    <Avatar user={p} size={28} />
                    <span className="min-w-0">
                      <span className="block truncate text-sm font-bold">
                        {p.display_name ?? p.login}
                      </span>
                      <span className="block truncate font-mono text-xs text-[var(--text-muted)]">
                        @{p.login}
                      </span>
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
