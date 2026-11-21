"use client";

import * as React from "react";

import { cn } from "@/lib/utils";
import type { UserPublic } from "@/lib/types";

/*
 * Avatar fallback chain:
 *   1. the real 42 photo (user.avatar_url), when it loads;
 *   2. a deterministic "funny" DiceBear avatar (same user -> same picture) if
 *      that image fails (e.g. the 42 CDN returns 403 on a hotlink);
 *   3. the user's initials if even that can't be reached.
 */

const STYLES = ["fun-emoji", "bottts", "croodles", "big-smile", "thumbs", "adventurer"] as const;

function hashString(s: string): number {
  let h = 5381;
  for (let i = 0; i < s.length; i++) h = ((h << 5) + h + s.charCodeAt(i)) >>> 0;
  return h;
}

function initials(u: Pick<UserPublic, "login" | "display_name">): string {
  const base = (u.display_name ?? u.login ?? "").trim();
  if (!base) return "42";
  const parts = base.split(/\s+/);
  if (parts.length >= 2) return (parts[0]![0]! + parts[1]![0]!).toUpperCase();
  return base.slice(0, 2).toUpperCase();
}

function funnyAvatarUrl(seed: string): string {
  // Seed the external service with a hash, not the real login, so the user's
  // 42 handle is never sent to dicebear.com. Still deterministic per user.
  const h = hashString(seed);
  const style = STYLES[h % STYLES.length]!;
  return `https://api.dicebear.com/9.x/${style}/svg?seed=${h.toString(36)}`;
}

export function Avatar({
  user,
  size = 34,
  className,
}: {
  user: Pick<UserPublic, "login" | "display_name" | "avatar_url">;
  size?: number;
  className?: string;
}) {
  const seed = user.login || user.display_name || "studente42";

  // Ordered image sources; when all fail we render initials.
  const sources = React.useMemo(() => {
    const list: string[] = [];
    if (user.avatar_url) list.push(user.avatar_url);
    list.push(funnyAvatarUrl(seed));
    return list;
  }, [user.avatar_url, seed]);

  const [idx, setIdx] = React.useState(0);

  // Reset to the preferred source when the user (or their photo) changes.
  React.useEffect(() => {
    setIdx(0);
  }, [sources]);

  const dim = { width: size, height: size };
  const src = sources[idx];

  if (src) {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img
        src={src}
        alt={user.login}
        style={dim}
        loading="lazy"
        onError={() => setIdx((i) => i + 1)}
        className={cn(
          "object-cover border border-[var(--border)] bg-[var(--surface-2)]",
          className,
        )}
      />
    );
  }

  return (
    <span
      style={dim}
      className={cn(
        "inline-flex items-center justify-center border border-[var(--border)] bg-[var(--cat-studio-bg)] text-[var(--cat-studio-fg)] font-mono font-bold text-xs",
        className,
      )}
    >
      {initials(user)}
    </span>
  );
}
