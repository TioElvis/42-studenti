"use client";

import * as React from "react";
import { MapPin, Clock, Users, ChevronRight, Star } from "lucide-react";

import { SectionHeading } from "@/components/chrome/section-heading";
import { Window, WindowBar } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { EventDetailModal } from "./event-detail-modal";
import { api, ApiError } from "@/lib/api";
import { useRealtime } from "@/providers/realtime";
import { useI18n } from "@/providers/i18n-provider";
import { cn } from "@/lib/utils";
import { dateBlock, timeRange } from "@/lib/time";
import type { EventItem, InterestState } from "@/lib/types";

/*
 * TODO (Step 2.1): add a "Proponi un evento" button + form here so students can
 * submit community events (POST /events on the backend). For now this grid is
 * read-only and shows only official 42 Roma events.
 */

export function EventsGrid() {
  const { t } = useI18n();
  const [events, setEvents] = React.useState<EventItem[] | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [selected, setSelected] = React.useState<EventItem | null>(null);

  const load = React.useCallback(async () => {
    setError(null);
    setEvents(null);
    try {
      setEvents(await api.listEvents());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("eventi.error"));
    }
  }, [t]);

  React.useEffect(() => {
    void load();
  }, [load]);

  // Live interest counts from other students.
  useRealtime((event) => {
    if (event.type !== "event.interest") return;
    setEvents((prev) =>
      prev
        ? prev.map((e) =>
            e.id === event.data.event_id
              ? { ...e, interest_count: event.data.interest_count }
              : e,
          )
        : prev,
    );
  });

  // Keep the grid in sync after this user toggles from the dialog.
  function applyInterest(eventId: number, state: InterestState) {
    setEvents((prev) =>
      prev
        ? prev.map((e) =>
            e.id === eventId
              ? { ...e, interested: state.interested, interest_count: state.interest_count }
              : e,
          )
        : prev,
    );
    setSelected((s) =>
      s && s.id === eventId
        ? { ...s, interested: state.interested, interest_count: state.interest_count }
        : s,
    );
  }

  return (
    <section>
      <SectionHeading label={t("eventi.label")} desc={t("eventi.desc")} />

      {error ? (
        <div className="window retro-shadow p-6 text-center">
          <p className="font-mono text-sm text-[var(--primary)]">{error}</p>
          <Button variant="outline" size="sm" className="mt-3" onClick={() => void load()}>
            {t("common.retry")}
          </Button>
        </div>
      ) : events === null ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-44 w-full" />
          ))}
        </div>
      ) : events.length === 0 ? (
        <div className="window retro-shadow p-8 text-center">
          <p className="font-display text-lg">{t("eventi.emptyTitle")}</p>
          <p className="mt-1 font-mono text-sm text-[var(--text-muted)]">{t("eventi.emptyHint")}</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {events.map((ev, i) => (
            <EventCard key={ev.id} event={ev} index={i} onOpen={() => setSelected(ev)} />
          ))}
        </div>
      )}

      <EventDetailModal
        event={selected}
        onOpenChange={(open) => !open && setSelected(null)}
        onInterestChange={applyInterest}
      />
    </section>
  );
}

function EventCard({
  event,
  index,
  onOpen,
}: {
  event: EventItem;
  index: number;
  onOpen: () => void;
}) {
  const { t, lang } = useI18n();
  const d = dateBlock(event.begin_at, lang);
  const time = timeRange(event.begin_at, event.end_at, lang);

  return (
    <Window
      className="retro-shadow hover-lift fade-up flex cursor-pointer flex-col"
      style={{ animationDelay: `${Math.min(index, 8) * 60}ms` }}
      role="button"
      tabIndex={0}
      aria-label={t("eventi.openEvent", { name: event.name ?? t("eventi.nameFallback") })}
      onClick={onOpen}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onOpen();
        }
      }}
    >
      <WindowBar title={`EVENTO_${String(event.id).slice(-4)}.ICS`} />
      <div className="flex gap-3 p-4">
        <div className="flex h-16 w-16 shrink-0 flex-col items-center justify-center border border-[var(--border)] bg-[var(--surface-2)]">
          <span className="font-display text-2xl font-bold leading-none">{d.day}</span>
          <span className="font-mono text-[10px] text-[var(--text-muted)]">{d.month}</span>
        </div>
        <div className="min-w-0 flex-1">
          <h3 className="font-display text-base font-bold leading-tight">
            {event.name ?? t("eventi.eventFallback")}
          </h3>
          {event.description && (
            <p className="mt-1 line-clamp-2 text-xs text-[var(--text-muted)]">
              {event.description}
            </p>
          )}
        </div>
      </div>

      <div className="flex flex-col gap-1.5 px-4 pb-3 font-mono text-xs text-[var(--text-muted)]">
        {event.location && (
          <span className="flex items-center gap-1.5">
            <MapPin className="h-3.5 w-3.5" /> {event.location}
          </span>
        )}
        {time && (
          <span className="flex items-center gap-1.5">
            <Clock className="h-3.5 w-3.5" /> {time}
          </span>
        )}
        {event.nbr_subscribers != null && (
          <span className="flex items-center gap-1.5">
            <Users className="h-3.5 w-3.5" /> {event.nbr_subscribers}
            {event.max_people ? ` / ${event.max_people}` : ""} {t("eventi.subscribers")}
          </span>
        )}
      </div>

      <div className="mt-auto flex items-center justify-between gap-2 border-t border-[var(--border-subtle)] px-4 py-2.5 font-mono text-xs">
        <span
          className={cn(
            "inline-flex items-center gap-1",
            event.interested ? "text-[var(--primary)]" : "text-[var(--text-muted)]",
          )}
        >
          <Star className={cn("h-3.5 w-3.5", event.interested && "fill-current")} />
          {event.interest_count}
        </span>
        <span className="inline-flex items-center gap-1 text-[var(--primary)]">
          {t("eventi.details")} <ChevronRight className="h-3.5 w-3.5" />
        </span>
      </div>
    </Window>
  );
}
