"use client";

import Link from "next/link";
import { MessageSquare, Pencil, Trash2 } from "lucide-react";

import { Avatar } from "@/components/chrome/avatar";
import { CategoryBadge } from "@/components/ui/badge";
import { Linkify } from "@/components/ui/linkify";
import { LikeButton } from "./like-button";
import { SondaggioBox } from "./sondaggio-box";
import { relativeTime } from "@/lib/time";
import { useI18n } from "@/providers/i18n-provider";
import type { LikeState, PollOption, Post, RsvpState } from "@/lib/types";

export function PostCard({
  post,
  index = 0,
  onOpen,
  onLike,
  onEdit,
  onDelete,
  onRsvp,
  onPoll,
  onOpenAttendees,
}: {
  post: Post;
  index?: number;
  onOpen: (post: Post) => void;
  onLike: (post: Post, state: LikeState) => void;
  onEdit: (post: Post) => void;
  onDelete: (post: Post) => void;
  onRsvp: (post: Post, state: RsvpState) => void;
  onPoll: (post: Post, options: PollOption[]) => void;
  onOpenAttendees: (post: Post) => void;
}) {
  const { t, lang } = useI18n();
  const isSondaggio = post.post_type === "sondaggio";

  return (
    <article
      className="window retro-shadow hover-lift fade-up cursor-pointer"
      style={{ animationDelay: `${Math.min(index, 8) * 60}ms` }}
      onClick={() => onOpen(post)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onOpen(post);
        }
      }}
    >
      <div className="p-4">
        <header className="mb-3 flex items-start justify-between gap-2">
          <div className="flex items-center gap-2.5">
            <Avatar user={post.author} />
            <div>
              <Link
                href={`/u/${post.author.login}`}
                onClick={(e) => e.stopPropagation()}
                className="font-mono text-sm font-bold hover:underline"
              >
                {post.author.login}
              </Link>
              <div className="font-mono text-[11px] text-[var(--text-muted)]">
                {relativeTime(post.created_at, lang)}
              </div>
            </div>
          </div>
          <div className="flex flex-wrap items-center justify-end gap-1.5">
            {isSondaggio && (
              <span className="cat-badge cat-cerco_team" title={t("post.sondaggioTitle")}>
                {t("post.sondaggioBadge")}
              </span>
            )}
            <CategoryBadge category={post.category} />
          </div>
        </header>

        {post.title && (
          <h3 className={`font-display text-base font-bold ${post.content ? "mb-1" : "mb-4"}`}>
            {post.title}
          </h3>
        )}
        {post.content && (
          <p className="mb-4 line-clamp-5 whitespace-pre-wrap break-words text-sm leading-relaxed">
            <Linkify>{post.content}</Linkify>
          </p>
        )}

        <footer className="flex flex-wrap items-center gap-2">
          <LikeButton
            postId={post.id}
            liked={post.liked_by_me}
            count={post.like_count}
            size="sm"
            onChange={(state) => onLike(post, state)}
          />
          <span className="inline-flex items-center gap-1.5 border border-[var(--border)] bg-[var(--surface)] px-2.5 py-1 font-mono text-xs text-[var(--text-muted)] retro-shadow-sm rounded-[var(--radius-pill)]">
            <MessageSquare className="h-3.5 w-3.5" />
            {post.comment_count}
          </span>

          {post.is_mine && (
            <span className="ml-auto flex items-center gap-1">
              <button
                type="button"
                aria-label={t("common.edit")}
                onClick={(e) => {
                  e.stopPropagation();
                  onEdit(post);
                }}
                className="inline-flex items-center gap-1 border border-[var(--border)] bg-[var(--surface)] px-2 py-1 font-mono text-xs hover:bg-[var(--surface-2)] rounded-[var(--radius-pill)]"
              >
                <Pencil className="h-3.5 w-3.5" /> {t("common.edit")}
              </button>
              <button
                type="button"
                aria-label={t("common.delete")}
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete(post);
                }}
                className="inline-flex items-center gap-1 border border-[var(--primary)] bg-[var(--surface)] px-2 py-1 font-mono text-xs text-[var(--primary)] hover:bg-[var(--primary)] hover:text-[var(--primary-fg)]"
              >
                <Trash2 className="h-3.5 w-3.5" /> {t("common.delete")}
              </button>
            </span>
          )}
        </footer>

        {isSondaggio && (
          <SondaggioBox
            post={post}
            onRsvpChange={(_id, state) => onRsvp(post, state)}
            onPollChange={(_id, options) => onPoll(post, options)}
            onOpenAttendees={() => onOpenAttendees(post)}
          />
        )}
      </div>
    </article>
  );
}
