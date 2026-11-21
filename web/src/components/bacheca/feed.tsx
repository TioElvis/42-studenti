"use client";

import * as React from "react";
import { Plus } from "lucide-react";

import { SectionHeading } from "@/components/chrome/section-heading";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { CategoryPills, type CategoryFilter } from "./category-pills";
import { PostCard } from "./post-card";
import { PostFormModal, type PostFormValues } from "./post-form-modal";
import { PostDetailModal, type PostPatch } from "./post-detail-modal";
import { AttendeesDialog } from "./attendees-dialog";
import { Sidebar } from "./sidebar";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { api, ApiError } from "@/lib/api";
import { useRealtime } from "@/providers/realtime";
import { useAuth } from "@/providers/auth-provider";
import { useI18n } from "@/providers/i18n-provider";
import type { LikeState, Post, PostType, RsvpState } from "@/lib/types";

const PAGE_SIZE = 15;

export interface FeedProps {
  /** When set, the feed shows only this post type (e.g. sondaggi for Comunità). */
  postType?: PostType;
}

export function Feed({ postType }: FeedProps = {}) {
  const { user } = useAuth();
  const { t } = useI18n();
  const isComunita = postType === "sondaggio";
  const [posts, setPosts] = React.useState<Post[]>([]);
  const [filter, setFilter] = React.useState<CategoryFilter>("all");
  const [loading, setLoading] = React.useState(true);
  const [loadingMore, setLoadingMore] = React.useState(false);
  const [cursor, setCursor] = React.useState<number | null>(null);
  const [hasMore, setHasMore] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const [formOpen, setFormOpen] = React.useState(false);
  const [editing, setEditing] = React.useState<Post | null>(null);
  const [detailPostId, setDetailPostId] = React.useState<number | null>(null);
  const [attendeesPostId, setAttendeesPostId] = React.useState<number | null>(null);
  const [pendingDelete, setPendingDelete] = React.useState<Post | null>(null);

  const load = React.useCallback(async (f: CategoryFilter) => {
    setLoading(true);
    setError(null);
    try {
      const page = await api.listPosts({
        category: f === "all" ? undefined : f,
        postType,
        limit: PAGE_SIZE,
      });
      setPosts(page.items);
      setCursor(page.next_cursor);
      setHasMore(page.next_cursor != null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("bacheca.error"));
    } finally {
      setLoading(false);
    }
  }, [postType, t]);

  React.useEffect(() => {
    void load(filter);
  }, [filter, load]);

  const loadMore = React.useCallback(async () => {
    if (loading || loadingMore || !hasMore || cursor == null) return;
    setLoadingMore(true);
    try {
      const page = await api.listPosts({
        category: filter === "all" ? undefined : filter,
        postType,
        cursor,
        limit: PAGE_SIZE,
      });
      setPosts((prev) => {
        const seen = new Set(prev.map((p) => p.id));
        return [...prev, ...page.items.filter((p) => !seen.has(p.id))];
      });
      setCursor(page.next_cursor);
      setHasMore(page.next_cursor != null);
    } catch {
      setHasMore(false); // stop trying on error; a filter change retries
    } finally {
      setLoadingMore(false);
    }
  }, [loading, loadingMore, hasMore, cursor, filter, postType]);

  // Infinite scroll: a sentinel near the bottom triggers loading older posts.
  const sentinelRef = React.useRef<HTMLDivElement | null>(null);
  React.useEffect(() => {
    const el = sentinelRef.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting) void loadMore();
      },
      { rootMargin: "500px 0px" },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [loadMore]);

  function patchPost(id: number, patch: PostPatch) {
    setPosts((prev) => prev.map((p) => (p.id === id ? { ...p, ...patch } : p)));
  }

  // Live updates from other students (and echoes of our own actions).
  useRealtime((event) => {
    const myId = user?.id ?? -1;
    switch (event.type) {
      case "post.created": {
        const incoming = event.data;
        setPosts((prev) => {
          if (prev.some((p) => p.id === incoming.id)) return prev; // de-dupe own echo
          if (postType && incoming.post_type !== postType) return prev;
          if (filter !== "all" && incoming.category !== filter) return prev;
          return [{ ...incoming, is_mine: incoming.author.id === myId }, ...prev];
        });
        break;
      }
      case "post.updated": {
        const incoming = event.data;
        setPosts((prev) =>
          prev
            .map((p) =>
              p.id === incoming.id
                ? {
                    ...p,
                    ...incoming,
                    is_mine: incoming.author.id === myId,
                    liked_by_me: p.liked_by_me,
                    joined_by_me: p.joined_by_me,
                  }
                : p,
            )
            .filter((p) => (filter === "all" ? true : p.category === filter)),
        );
        break;
      }
      case "post.deleted":
        setPosts((prev) => prev.filter((p) => p.id !== event.data.id));
        break;
      case "post.like":
        setPosts((prev) =>
          prev.map((p) =>
            p.id === event.data.post_id ? { ...p, like_count: event.data.like_count } : p,
          ),
        );
        break;
      case "post.rsvp":
        setPosts((prev) =>
          prev.map((p) =>
            p.id === event.data.post_id
              ? { ...p, rsvp_count: event.data.rsvp_count, rsvp_full: event.data.rsvp_full }
              : p,
          ),
        );
        break;
      case "comment.created":
      case "comment.deleted":
        setPosts((prev) =>
          prev.map((p) =>
            p.id === event.data.post_id ? { ...p, comment_count: event.data.comment_count } : p,
          ),
        );
        break;
    }
  });

  function handleLike(post: Post, state: LikeState) {
    patchPost(post.id, { liked_by_me: state.liked, like_count: state.like_count });
  }

  function handleRsvp(post: Post, state: RsvpState) {
    patchPost(post.id, {
      joined_by_me: state.joined,
      rsvp_count: state.rsvp_count,
      rsvp_full: state.rsvp_full,
    });
  }

  async function handleSubmit(values: PostFormValues) {
    const body = {
      title: values.title || null,
      content: values.content,
      category: values.category,
      post_type: values.postType,
      max_participants: values.maxParticipants,
    };
    if (editing) {
      const updated = await api.updatePost(editing.id, {
        title: body.title,
        content: body.content,
        category: body.category,
        // Capacity is editable only on a sondaggio; post type stays fixed.
        ...(editing.post_type === "sondaggio"
          ? { max_participants: body.max_participants }
          : {}),
      });
      setPosts((prev) =>
        prev
          .map((p) => (p.id === updated.id ? { ...p, ...updated } : p))
          .filter((p) => (filter === "all" ? true : p.category === filter)),
      );
    } else {
      const created = await api.createPost(body);
      // De-dupe: the WebSocket "post.created" echo may already have added it.
      const matchesType = !postType || created.post_type === postType;
      if (matchesType && (filter === "all" || filter === created.category)) {
        setPosts((prev) => (prev.some((p) => p.id === created.id) ? prev : [created, ...prev]));
      }
    }
  }

  async function confirmDelete() {
    const post = pendingDelete;
    if (!post) return;
    const snapshot = posts;
    setPosts((prev) => prev.filter((p) => p.id !== post.id));
    try {
      await api.deletePost(post.id);
    } catch {
      setPosts(snapshot); // revert on failure
    }
  }

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1.6fr_1fr]">
      <section className="order-2 lg:order-1">
        <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
          <SectionHeading
            label={t(isComunita ? "comunita.label" : "bacheca.label")}
            desc={t(isComunita ? "comunita.desc" : "bacheca.desc")}
          />
          {!postType && (
            <Button
              onClick={() => {
                setEditing(null);
                setFormOpen(true);
              }}
            >
              <Plus className="h-4 w-4" /> {t("bacheca.newMessage")}
            </Button>
          )}
        </div>

        <div className="mb-5">
          <CategoryPills value={filter} onChange={setFilter} />
        </div>

        {loading ? (
          <div className="flex flex-col gap-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-40 w-full" />
            ))}
          </div>
        ) : error ? (
          <div className="window retro-shadow p-6 text-center">
            <p className="font-mono text-sm text-[var(--primary)]">{error}</p>
            <Button variant="outline" size="sm" className="mt-3" onClick={() => void load(filter)}>
              {t("common.retry")}
            </Button>
          </div>
        ) : posts.length === 0 ? (
          <div className="window retro-shadow p-8 text-center">
            <p className="font-display text-lg">{t("bacheca.emptyTitle")}</p>
            <p className="mt-1 font-mono text-sm text-[var(--text-muted)]">
              {t(isComunita ? "bacheca.emptyHintComunita" : "bacheca.emptyHintPost")}
            </p>
          </div>
        ) : (
          <>
            <div className="flex flex-col gap-4">
              {posts.map((post, i) => (
                <PostCard
                  key={post.id}
                  post={post}
                  index={i}
                  onOpen={(p) => setDetailPostId(p.id)}
                  onLike={handleLike}
                  onRsvp={handleRsvp}
                  onOpenAttendees={(p) => setAttendeesPostId(p.id)}
                  onEdit={(p) => {
                    setEditing(p);
                    setFormOpen(true);
                  }}
                  onDelete={(p) => setPendingDelete(p)}
                />
              ))}
            </div>

            {/* Infinite-scroll sentinel + skeletons while fetching older posts. */}
            <div ref={sentinelRef} aria-hidden className="h-1" />
            {loadingMore && (
              <div className="mt-4 flex flex-col gap-4">
                <Skeleton className="h-28 w-full" />
                <Skeleton className="h-28 w-full" />
              </div>
            )}
            {!hasMore && (
              <p className="mt-6 text-center font-mono text-xs text-[var(--text-muted)]">
                {t("bacheca.endOfFeed")}
              </p>
            )}
          </>
        )}
      </section>

      <Sidebar className="order-1 lg:order-2" onOpenPost={(id) => setDetailPostId(id)} />

      <PostFormModal
        open={formOpen}
        onOpenChange={setFormOpen}
        editing={editing}
        onSubmit={handleSubmit}
      />
      <PostDetailModal
        postId={detailPostId}
        onOpenChange={(open) => {
          if (!open) setDetailPostId(null);
        }}
        onPatch={patchPost}
        onOpenAttendees={(id) => setAttendeesPostId(id)}
      />
      <AttendeesDialog
        postId={attendeesPostId}
        onOpenChange={(open) => !open && setAttendeesPostId(null)}
      />
      <ConfirmDialog
        open={pendingDelete != null}
        onOpenChange={(open) => !open && setPendingDelete(null)}
        title={t("bacheca.deleteTitle")}
        description={t("bacheca.deleteDesc")}
        confirmLabel={t("bacheca.deleteConfirm")}
        cancelLabel={t("bacheca.deleteCancel")}
        onConfirm={confirmDelete}
      />
    </div>
  );
}
