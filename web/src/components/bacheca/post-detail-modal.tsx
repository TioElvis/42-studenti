"use client";

import * as React from "react";
import Link from "next/link";
import * as DialogPrimitive from "@radix-ui/react-dialog";

import { DialogContent } from "@/components/ui/dialog";
import { Avatar } from "@/components/chrome/avatar";
import { CategoryBadge } from "@/components/ui/badge";
import { LikeButton } from "./like-button";
import { CommentList } from "./comment-list";
import { SondaggioBox } from "./sondaggio-box";
import { Skeleton } from "@/components/ui/skeleton";
import { Linkify } from "@/components/ui/linkify";
import { relativeTime } from "@/lib/time";
import { api } from "@/lib/api";
import { useTheme } from "@/providers/theme-provider";
import { useRealtime } from "@/providers/realtime";
import { useAuth } from "@/providers/auth-provider";
import { useI18n } from "@/providers/i18n-provider";
import type { Comment, LikeState, PostDetail, RsvpState } from "@/lib/types";

export interface PostPatch {
  like_count?: number;
  liked_by_me?: boolean;
  comment_count?: number;
  rsvp_count?: number;
  rsvp_full?: boolean;
  joined_by_me?: boolean;
}

export function PostDetailModal({
  postId,
  onOpenChange,
  onPatch,
  onOpenAttendees,
}: {
  postId: number | null;
  onOpenChange: (open: boolean) => void;
  onPatch: (postId: number, patch: PostPatch) => void;
  onOpenAttendees: (postId: number) => void;
}) {
  const { theme } = useTheme();
  const { user } = useAuth();
  const { t, lang } = useI18n();
  const hacker = theme === "hacker";
  const [detail, setDetail] = React.useState<PostDetail | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (postId == null) {
      setDetail(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    api
      .getPost(postId)
      .then((d) => {
        if (!cancelled) setDetail(d);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : t("postDetail.loadError"));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [postId, t]);

  // Live updates for the post currently open in the thread view.
  useRealtime((event) => {
    if (postId == null) return;
    const myId = user?.id ?? -1;
    switch (event.type) {
      case "post.like":
        if (event.data.post_id === postId) {
          setDetail((d) => (d ? { ...d, like_count: event.data.like_count } : d));
        }
        break;
      case "post.updated":
        if (event.data.id === postId) {
          const incoming = event.data;
          setDetail((d) =>
            d
              ? {
                  ...d,
                  ...incoming,
                  comments: d.comments,
                  liked_by_me: d.liked_by_me,
                  is_mine: incoming.author.id === myId,
                }
              : d,
          );
        }
        break;
      case "post.deleted":
        if (event.data.id === postId) onOpenChange(false);
        break;
      case "post.rsvp":
        if (event.data.post_id === postId) {
          setDetail((d) =>
            d ? { ...d, rsvp_count: event.data.rsvp_count, rsvp_full: event.data.rsvp_full } : d,
          );
        }
        break;
      case "comment.created":
        if (event.data.post_id === postId) {
          const incoming = event.data;
          setDetail((d) => {
            if (!d) return d;
            if (d.comments.some((c) => c.id === incoming.comment.id)) {
              return { ...d, comment_count: incoming.comment_count };
            }
            const c: Comment = {
              ...incoming.comment,
              is_mine: incoming.comment.author.id === myId,
            };
            return { ...d, comments: [...d.comments, c], comment_count: incoming.comment_count };
          });
        }
        break;
      case "comment.deleted":
        if (event.data.post_id === postId) {
          const incoming = event.data;
          setDetail((d) =>
            d
              ? {
                  ...d,
                  comments: d.comments.filter((c) => c.id !== incoming.comment_id),
                  comment_count: incoming.comment_count,
                }
              : d,
          );
        }
        break;
    }
  });

  function handleLike(state: LikeState) {
    if (!detail) return;
    setDetail({ ...detail, liked_by_me: state.liked, like_count: state.like_count });
    onPatch(detail.id, { liked_by_me: state.liked, like_count: state.like_count });
  }

  function handleRsvp(state: RsvpState) {
    if (!detail) return;
    const patch = {
      joined_by_me: state.joined,
      rsvp_count: state.rsvp_count,
      rsvp_full: state.rsvp_full,
    };
    setDetail({ ...detail, ...patch });
    onPatch(detail.id, patch);
  }

  function handleAddComment(comment: Comment) {
    if (!detail) return;
    const next = { ...detail, comments: [...detail.comments, comment], comment_count: detail.comment_count + 1 };
    setDetail(next);
    onPatch(detail.id, { comment_count: next.comment_count });
  }

  function handleDeleteComment(commentId: number) {
    if (!detail) return;
    const next = {
      ...detail,
      comments: detail.comments.filter((c) => c.id !== commentId),
      comment_count: Math.max(0, detail.comment_count - 1),
    };
    setDetail(next);
    onPatch(detail.id, { comment_count: next.comment_count });
  }

  return (
    <DialogPrimitive.Root open={postId != null} onOpenChange={onOpenChange}>
      <DialogContent title={t("postDetail.title")} barTitle={t("postDetail.bar")}>
        {loading && (
          <div className="flex flex-col gap-3">
            <Skeleton className="h-6 w-1/3" />
            <Skeleton className="h-20 w-full" />
            <Skeleton className="h-10 w-full" />
          </div>
        )}
        {error && (
          <p className="font-mono text-sm text-[var(--primary)]" role="alert">
            {error}
          </p>
        )}
        {detail && !loading && (
          <div className="flex flex-col gap-4">
            <header className="flex items-start justify-between gap-2">
              <div className="flex items-center gap-2.5">
                <Avatar user={detail.author} />
                <div>
                  <Link
                  href={`/u/${detail.author.login}`}
                  className="font-mono text-sm font-bold hover:underline"
                >
                  @{detail.author.login}
                </Link>
                  <div className="font-mono text-[11px] text-[var(--text-muted)]">
                    {relativeTime(detail.created_at, lang)}
                  </div>
                </div>
              </div>
              <CategoryBadge category={detail.category} terminal={hacker} />
            </header>

            {detail.title && <h3 className="font-display text-lg font-bold">{detail.title}</h3>}
            <p className="whitespace-pre-wrap break-words text-sm leading-relaxed">
              <Linkify>{detail.content}</Linkify>
            </p>

            <div>
              <LikeButton
                postId={detail.id}
                liked={detail.liked_by_me}
                count={detail.like_count}
                onChange={handleLike}
              />
            </div>

            {detail.post_type === "sondaggio" && (
              <SondaggioBox
                post={detail}
                onRsvpChange={(_id, state) => handleRsvp(state)}
                onOpenAttendees={(id) => onOpenAttendees(id)}
              />
            )}

            <hr className="border-[var(--border-subtle)]" />

            <CommentList
              postId={detail.id}
              comments={detail.comments}
              onAdd={handleAddComment}
              onDelete={handleDeleteComment}
            />
          </div>
        )}
      </DialogContent>
    </DialogPrimitive.Root>
  );
}
