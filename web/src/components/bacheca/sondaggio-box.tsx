"use client";

import * as React from "react";
import { Users, Check } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { api, ApiError } from "@/lib/api";
import { useI18n } from "@/providers/i18n-provider";
import type { PollOption, Post, RsvpState } from "@/lib/types";

/**
 * The poll box attached under a sondaggio, linked to the card by a vertical
 * line. Renders either the classic attendance tracker ("Ci sto!") or a
 * WhatsApp-style options poll, depending on the post's poll_mode.
 */
export function SondaggioBox({
  post,
  onRsvpChange,
  onPollChange,
  onOpenAttendees,
}: {
  post: Post;
  onRsvpChange: (postId: number, state: RsvpState) => void;
  onPollChange: (postId: number, options: PollOption[]) => void;
  onOpenAttendees: (postId: number) => void;
}) {
  const { t } = useI18n();
  return (
    <div className="relative mt-3 pl-5" onClick={(e) => e.stopPropagation()}>
      <span aria-hidden className="absolute left-2 top-0 h-full w-px bg-[var(--border)]" />
      <span aria-hidden className="absolute left-2 top-5 h-px w-3 bg-[var(--border)]" />

      <div className="window retro-shadow-sm">
        <div className="window-bar">
          <span>{t("sondaggio.bar")}</span>
        </div>
        {post.poll_mode === "options" ? (
          <OptionsPoll post={post} onPollChange={onPollChange} />
        ) : (
          <AttendanceControls
            post={post}
            onRsvpChange={onRsvpChange}
            onOpenAttendees={onOpenAttendees}
          />
        )}
      </div>
    </div>
  );
}

function AttendanceControls({
  post,
  onRsvpChange,
  onOpenAttendees,
}: {
  post: Post;
  onRsvpChange: (postId: number, state: RsvpState) => void;
  onOpenAttendees: (postId: number) => void;
}) {
  const { t } = useI18n();
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const joined = post.joined_by_me;
  const full = post.rsvp_full;
  const capacity =
    post.max_participants == null
      ? `${post.rsvp_count} ${t("sondaggio.participants")}`
      : `${post.rsvp_count}/${post.max_participants} ${t("sondaggio.participants")}`;

  async function toggle(e: React.MouseEvent) {
    e.stopPropagation();
    if (busy || (full && !joined)) return;
    setBusy(true);
    setError(null);
    try {
      const state = await api.toggleRsvp(post.id);
      onRsvpChange(post.id, state);
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 409
          ? t("sondaggio.errFull")
          : err instanceof ApiError
            ? err.message
            : t("sondaggio.errGeneric"),
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <div className="flex flex-wrap items-center justify-between gap-3 p-3">
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onOpenAttendees(post.id);
          }}
          className="inline-flex items-center gap-1.5 border border-[var(--border)] bg-[var(--surface)] px-2.5 py-1 font-mono text-xs hover:bg-[var(--surface-2)] rounded-[var(--radius-pill)]"
        >
          <Users className="h-3.5 w-3.5" />
          {capacity}
        </button>

        <Button
          variant={joined ? "primary" : "outline"}
          size="sm"
          disabled={busy || (full && !joined)}
          aria-pressed={joined}
          onClick={toggle}
          className={cn("group min-w-28 justify-center", busy && "opacity-70")}
        >
          {full && !joined ? (
            t("sondaggio.full")
          ) : joined ? (
            <>
              <Check className="h-3.5 w-3.5" />
              <span className="group-hover:hidden">{t("sondaggio.join")}</span>
              <span className="hidden group-hover:inline">{t("sondaggio.leave")}</span>
            </>
          ) : (
            t("sondaggio.join")
          )}
        </Button>
      </div>
      {error && (
        <p className="px-3 pb-3 font-mono text-xs text-[var(--primary)]" role="alert">
          {error}
        </p>
      )}
    </>
  );
}

function OptionsPoll({
  post,
  onPollChange,
}: {
  post: Post;
  onPollChange: (postId: number, options: PollOption[]) => void;
}) {
  const { t } = useI18n();
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const total = post.poll_options.reduce((sum, o) => sum + o.vote_count, 0);

  async function vote(e: React.MouseEvent, optionId: number) {
    e.stopPropagation();
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      const state = await api.votePoll(post.id, optionId);
      onPollChange(post.id, state.options);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("sondaggio.voteError"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-2 p-3">
      <p className="font-mono text-[11px] text-[var(--text-muted)]">
        {post.poll_multi ? t("sondaggio.multi") : t("sondaggio.single")}
      </p>
      {post.poll_options.map((o) => {
        const pct = total > 0 ? Math.round((o.vote_count / total) * 100) : 0;
        return (
          <button
            key={o.id}
            type="button"
            disabled={busy}
            aria-pressed={o.voted_by_me}
            onClick={(e) => vote(e, o.id)}
            className={cn(
              "relative overflow-hidden border px-2.5 py-2 text-left transition-colors rounded-[var(--radius-inner)]",
              o.voted_by_me
                ? "border-[var(--ring)] bg-[var(--surface)]"
                : "border-[var(--border)] bg-[var(--surface)] hover:bg-[var(--surface-2)]",
              busy && "opacity-70",
            )}
          >
            {/* Proportional vote bar behind the label. */}
            <span
              aria-hidden
              className="absolute inset-y-0 left-0 bg-[var(--surface-2)]"
              style={{ width: `${pct}%` }}
            />
            <span className="relative flex items-center justify-between gap-2 font-mono text-xs">
              <span className="flex min-w-0 items-center gap-1.5">
                <span
                  aria-hidden
                  className={cn(
                    "flex h-3.5 w-3.5 shrink-0 items-center justify-center border",
                    post.poll_multi ? "" : "rounded-full",
                    o.voted_by_me
                      ? "border-[var(--ring)] bg-[var(--primary)] text-[var(--primary-fg)]"
                      : "border-[var(--border)]",
                  )}
                >
                  {o.voted_by_me && <Check className="h-2.5 w-2.5" />}
                </span>
                <span className="truncate">{o.text}</span>
              </span>
              <span className="shrink-0 tabular-nums text-[var(--text-muted)]">
                {o.vote_count} · {pct}%
              </span>
            </span>
          </button>
        );
      })}
      <p className="font-mono text-[11px] text-[var(--text-muted)]">
        {total} {t("sondaggio.votesWord")}
      </p>
      {error && (
        <p className="font-mono text-xs text-[var(--primary)]" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
