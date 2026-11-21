"use client";

import * as React from "react";
import { Users, Check } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { api, ApiError } from "@/lib/api";
import { useI18n } from "@/providers/i18n-provider";
import type { Post, RsvpState } from "@/lib/types";

/**
 * The attendance tracker attached under a sondaggio post, linked to the card by
 * a vertical line. "Ci sto!" is kept entirely separate from the like button.
 */
export function SondaggioBox({
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
    // The vertical connector line links the post card to the RSVP box.
    <div className="relative mt-3 pl-5" onClick={(e) => e.stopPropagation()}>
      <span aria-hidden className="absolute left-2 top-0 h-full w-px bg-[var(--border)]" />
      <span aria-hidden className="absolute left-2 top-5 h-px w-3 bg-[var(--border)]" />

      <div className="window retro-shadow-sm">
        <div className="window-bar">
          <span>{t("sondaggio.bar")}</span>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-3 p-3">
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onOpenAttendees(post.id);
            }}
            className="inline-flex items-center gap-1.5 border border-[var(--border)] bg-[var(--surface)] px-2.5 py-1 font-mono text-xs hover:bg-[var(--surface-2)]"
          >
            <Users className="h-3.5 w-3.5" />
            {capacity}
          </button>

          <Button
            variant={joined ? "primary" : full ? "outline" : "outline"}
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
      </div>
    </div>
  );
}
