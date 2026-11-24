"use client";

import * as React from "react";
import Link from "next/link";
import { Pin } from "lucide-react";

import { Window, WindowBar } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { EventDetailModal } from "@/components/eventi/event-detail-modal";
import { cn } from "@/lib/utils";
import { dateBlock } from "@/lib/time";
import { api } from "@/lib/api";
import { useI18n } from "@/providers/i18n-provider";
import type { EventItem, Post } from "@/lib/types";

export function Sidebar({
  className,
  onOpenPost,
  onShowSondaggi,
}: {
  className?: string;
  /** Opens a post in the shared detail dialog (owned by the Feed). */
  onOpenPost?: (postId: number) => void;
  /** Activates the Sondaggi filter on the Bacheca (owned by the Feed). */
  onShowSondaggi?: () => void;
}) {
  return (
    <aside className={cn("flex min-w-0 flex-col gap-4", className)}>
      {/* On mobile: MESSAGGIO FISSATO first, then the events / community cards.
          On lg: keep the cards on top of the sidebar column. */}
      <div className="order-1 lg:order-3">
        <PinnedNotice />
      </div>
      <div className="order-2 lg:order-1">
        <UpcomingEvents />
      </div>
      <div className="order-3 lg:order-2">
        <CommunityEvents onOpenPost={onOpenPost} onShowSondaggi={onShowSondaggi} />
      </div>
    </aside>
  );
}

/** Card teaser for the "eventi non ufficiali": the latest community sondaggi. */
function CommunityEvents({
  onOpenPost,
  onShowSondaggi,
}: {
  onOpenPost?: (postId: number) => void;
  onShowSondaggi?: () => void;
}) {
  const { t } = useI18n();
  const [polls, setPolls] = React.useState<Post[] | null>(null);
  const [failed, setFailed] = React.useState(false);

  React.useEffect(() => {
    let cancelled = false;
    api
      .listPosts({ postType: "sondaggio", limit: 3 })
      .then((page) => {
        if (!cancelled) setPolls(page.items);
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <Window className="retro-shadow">
      <WindowBar title={t("sidebar.communityBar")} />
      <div className="flex flex-col gap-2 p-3">
        {polls === null && !failed && (
          <>
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
          </>
        )}
        {failed && (
          <p className="font-mono text-xs text-[var(--text-muted)]">
            {t("sidebar.communityFailed")}
          </p>
        )}
        {polls && polls.length === 0 && (
          <p className="font-mono text-xs text-[var(--text-muted)]">
            {t("sidebar.communityEmpty")}
          </p>
        )}
        {polls?.map((p) => {
          const body = (
            <div className="min-w-0 flex-1">
              <div className="truncate font-mono text-xs font-bold">{p.title ?? p.content}</div>
              <div className="truncate font-mono text-[11px] text-[var(--text-muted)]">
                {p.rsvp_count}
                {p.max_participants ? `/${p.max_participants}` : ""} {t("sidebar.inWord")}
                {p.rsvp_full ? ` · ${t("common.full")}` : ""}
              </div>
            </div>
          );
          const cls =
            "flex w-full items-center gap-3 border border-[var(--border-subtle)] p-2 text-left transition-colors hover:border-[var(--border)] hover:bg-[var(--surface-2)]";
          // Clicking opens the full post dialog (handled by the Feed); without a
          // handler we fall back to activating the Sondaggi filter.
          return (
            <button
              key={p.id}
              type="button"
              onClick={() => (onOpenPost ? onOpenPost(p.id) : onShowSondaggi?.())}
              aria-label={t("sidebar.openPost", { name: p.title ?? t("sidebar.pollFallback") })}
              className={cls}
            >
              {body}
            </button>
          );
        })}
        <button
          type="button"
          onClick={() => onShowSondaggi?.()}
          className="mt-1 text-center font-mono text-xs text-[var(--primary)] hover:underline"
        >
          {t("sidebar.communityAll")}
        </button>
      </div>
    </Window>
  );
}

function PinnedNotice() {
  const { t } = useI18n();
  return (
    <div
      className="border border-[var(--border)] p-4 retro-shadow"
      style={{
        background: "var(--cat-evento_casuale-bg)",
        color: "var(--cat-evento_casuale-fg)",
      }}
    >
      <div className="mb-1.5 flex items-center gap-1.5 font-mono text-[11px] font-bold">
        <Pin className="h-3.5 w-3.5" /> {t("sidebar.pinnedLabel")}
      </div>
      <p className="text-sm leading-relaxed">{t("sidebar.pinnedBody")}</p>
    </div>
  );
}

function UpcomingEvents() {
  const { t, lang } = useI18n();
  const [events, setEvents] = React.useState<EventItem[] | null>(null);
  const [failed, setFailed] = React.useState(false);
  const [selected, setSelected] = React.useState<EventItem | null>(null);

  React.useEffect(() => {
    let cancelled = false;
    api
      .listEvents()
      .then((list) => {
        if (!cancelled) setEvents(list.slice(0, 3));
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <>
    <Window className="retro-shadow">
      <WindowBar title={t("sidebar.eventsBar")} />
      <div className="flex flex-col gap-2 p-3">
        {events === null && !failed && (
          <>
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-12 w-full" />
          </>
        )}
        {failed && (
          <p className="font-mono text-xs text-[var(--text-muted)]">{t("sidebar.eventsFailed")}</p>
        )}
        {events && events.length === 0 && (
          <p className="font-mono text-xs text-[var(--text-muted)]">{t("sidebar.eventsEmpty")}</p>
        )}
        {events?.map((ev) => {
          const d = dateBlock(ev.begin_at, lang);
          return (
            <button
              key={ev.id}
              type="button"
              onClick={() => setSelected(ev)}
              aria-label={t("sidebar.openEvent", { name: ev.name ?? t("sidebar.eventFallback") })}
              className="flex w-full items-center gap-3 border border-[var(--border-subtle)] p-2 text-left transition-colors hover:border-[var(--border)] hover:bg-[var(--surface-2)]"
            >
              <div className="flex w-11 shrink-0 flex-col items-center border border-[var(--border)] bg-[var(--surface-2)] py-1">
                <span className="font-display text-base font-bold leading-none">{d.day}</span>
                <span className="font-mono text-[9px] text-[var(--text-muted)]">{d.month}</span>
              </div>
              <div className="min-w-0 flex-1">
                <div className="truncate font-mono text-xs font-bold">
                  {ev.name ?? t("sidebar.eventFallback")}
                </div>
                <div className="truncate font-mono text-[11px] text-[var(--text-muted)]">
                  {ev.location ?? "42 Roma"}
                </div>
              </div>
            </button>
          );
        })}
        <Link
          href="/eventi"
          className="mt-1 text-center font-mono text-xs text-[var(--primary)] hover:underline"
        >
          {t("sidebar.allEvents")}
        </Link>
      </div>
    </Window>
    <EventDetailModal
      event={selected}
      onOpenChange={(open) => !open && setSelected(null)}
      onInterestChange={(id, state) => {
        setEvents((prev) =>
          prev
            ? prev.map((e) =>
                e.id === id
                  ? { ...e, interested: state.interested, interest_count: state.interest_count }
                  : e,
              )
            : prev,
        );
        setSelected((s) =>
          s && s.id === id
            ? { ...s, interested: state.interested, interest_count: state.interest_count }
            : s,
        );
      }}
    />
    </>
  );
}
