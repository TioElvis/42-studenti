"use client";

import * as React from "react";

import { cn } from "@/lib/utils";
import { api } from "@/lib/api";
import type { LikeState } from "@/lib/types";

export function LikeButton({
  postId,
  liked,
  count,
  onChange,
  size = "md",
}: {
  postId: number;
  liked: boolean;
  count: number;
  onChange: (state: LikeState) => void;
  size?: "sm" | "md";
}) {
  const [pending, setPending] = React.useState(false);
  const [popKey, setPopKey] = React.useState(0);

  async function handleClick(e: React.MouseEvent) {
    e.stopPropagation();
    if (pending) return;
    setPending(true);

    // Optimistic flip.
    const optimistic: LikeState = { liked: !liked, like_count: count + (liked ? -1 : 1) };
    onChange(optimistic);
    if (!liked) setPopKey((k) => k + 1);

    try {
      const real = await api.toggleLike(postId);
      onChange(real);
    } catch {
      onChange({ liked, like_count: count }); // revert
    } finally {
      setPending(false);
    }
  }

  return (
    <button
      type="button"
      onClick={handleClick}
      aria-pressed={liked}
      disabled={pending}
      className={cn(
        "inline-flex items-center gap-1.5 border border-[var(--border)] font-mono transition-colors retro-shadow-sm hover-lift disabled:opacity-60",
        size === "sm" ? "px-2.5 py-1 text-xs" : "px-3.5 py-2 text-sm",
        liked
          ? "bg-[var(--primary)] text-[var(--primary-fg)]"
          : "bg-[var(--surface)] text-[var(--text)] hover:bg-[var(--surface-2)]",
      )}
    >
      <span key={popKey} className={cn("inline-block", popKey > 0 && "heart-pop")} aria-hidden>
        ♥
      </span>
      <span>Daje!</span>
      <span className="tabular-nums">({count})</span>
    </button>
  );
}
