"use client";

import * as React from "react";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import { Calendar, Clock, MapPin, Users, Tag, Star } from "lucide-react";

import { DialogContent } from "@/components/ui/dialog";
import { EventScopeBadge } from "./event-scope-badge";
import { Button } from "@/components/ui/button";
import { Linkify } from "@/components/ui/linkify";
import { cn } from "@/lib/utils";
import { api, ApiError } from "@/lib/api";
import { useI18n } from "@/providers/i18n-provider";
import { fullDate, timeRange } from "@/lib/time";
import type { EventItem, InterestState } from "@/lib/types";

function InfoRow({
  icon: Icon,
  children,
}: {
  icon: React.ComponentType<{ className?: string }>;
  children: React.ReactNode;
}) {
  return (
    <div className="flex items-start gap-2.5 font-mono text-sm">
      <Icon className="mt-0.5 h-4 w-4 shrink-0 text-[var(--text-muted)]" />
      <span className="min-w-0">{children}</span>
    </div>
  );
}

export function EventDetailModal({
  event,
  onOpenChange,
  onInterestChange,
}: {
  event: EventItem | null;
  onOpenChange: (open: boolean) => void;
  /** Notifies the parent list so its card stays in sync after a toggle. */
  onInterestChange?: (eventId: number, state: InterestState) => void;
}) {
  const { t, lang } = useI18n();
  const [interested, setInterested] = React.useState(false);
  const [count, setCount] = React.useState(0);
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  // Seed from the event each time a different one opens.
  React.useEffect(() => {
    setInterested(event?.interested ?? false);
    setCount(event?.interest_count ?? 0);
    setError(null);
  }, [event?.id, event?.interested, event?.interest_count]);

  async function toggleInterest() {
    if (!event || busy) return;
    setBusy(true);
    setError(null);
    // Optimistic flip.
    const optimistic = { interested: !interested, interest_count: count + (interested ? -1 : 1) };
    setInterested(optimistic.interested);
    setCount(optimistic.interest_count);
    try {
      const real = await api.toggleEventInterest(event.id);
      setInterested(real.interested);
      setCount(real.interest_count);
      onInterestChange?.(event.id, real);
    } catch (err) {
      setInterested(interested); // revert
      setCount(count);
      setError(err instanceof ApiError ? err.message : t("eventDetail.errGeneric"));
    } finally {
      setBusy(false);
    }
  }

  const time = timeRange(event?.begin_at ?? null, event?.end_at ?? null);

  return (
    <DialogPrimitive.Root open={event != null} onOpenChange={onOpenChange}>
      <DialogContent title={event?.name ?? t("eventDetail.titleFallback")} barTitle="EVENTO.ICS">
        {event && (
          <div className="flex flex-col gap-4">
            <div>
              <EventScopeBadge internal={event.internal} />
            </div>
            <div className="flex flex-col gap-2.5">
              <InfoRow icon={Calendar}>
                <span className="capitalize">
                  {fullDate(event.begin_at, lang) ?? t("eventDetail.dateTBD")}
                </span>
              </InfoRow>
              {time && <InfoRow icon={Clock}>{time}</InfoRow>}
              <InfoRow icon={MapPin}>{event.location ?? "42 Roma"}</InfoRow>
              {event.kind && (
                <InfoRow icon={Tag}>
                  <span className="capitalize">{event.kind}</span>
                </InfoRow>
              )}
              {event.nbr_subscribers != null && (
                <InfoRow icon={Users}>
                  {event.nbr_subscribers}
                  {event.max_people ? ` / ${event.max_people}` : ""} {t("eventDetail.subscribers")}
                </InfoRow>
              )}
            </div>

            {event.description && (
              <div className="border-t border-[var(--border-subtle)] pt-3">
                <p className="whitespace-pre-wrap break-words text-sm leading-relaxed">
                  <Linkify>{event.description}</Linkify>
                </p>
              </div>
            )}

            <div className="flex flex-col gap-1.5">
              <Button
                variant={interested ? "primary" : "outline"}
                className={cn("w-full justify-center", interested && "heart-pop")}
                onClick={toggleInterest}
                disabled={busy}
                aria-pressed={interested}
              >
                <Star className="h-4 w-4" />
                {interested ? t("eventDetail.interested") : t("eventDetail.interest")}
              </Button>
              <p className="text-center font-mono text-xs text-[var(--text-muted)]">
                {count === 0
                  ? t("eventDetail.noneYet")
                  : `${count} ${count === 1 ? t("eventDetail.subOne") : t("eventDetail.subMany")}`}
              </p>
              {error && (
                <p className="text-center font-mono text-xs text-[var(--primary)]" role="alert">
                  {error}
                </p>
              )}
            </div>
          </div>
        )}
      </DialogContent>
    </DialogPrimitive.Root>
  );
}
