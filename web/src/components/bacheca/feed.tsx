"use client";

import * as React from "react";
import { Plus } from "lucide-react";

import { SectionHeading } from "@/components/chrome/section-heading";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { CategoryPills } from "./category-pills";
import { PostCard } from "./post-card";
import { PostFormModal, type PostFormValues } from "./post-form-modal";
import { PostDetailModal, type PostPatch } from "./post-detail-modal";
import { AttendeesDialog } from "./attendees-dialog";
import { Sidebar } from "./sidebar";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { api, ApiError } from "@/lib/api";
import { cn } from "@/lib/utils";
import { useRealtime } from "@/providers/realtime";
import { useAuth } from "@/providers/auth-provider";
import { useI18n } from "@/providers/i18n-provider";
import type { LikeState, PollOption, Post, PostCategory, RsvpState } from "@/lib/types";

const PAGE_SIZE = 15;

export function Feed() {
  const { user } = useAuth();
  const { t } = useI18n();
  const [posts, setPosts] = React.useState<Post[]>([]);
  // Empty set = no category filter ("Tutti"); any selected = show any-of.
  const [categories, setCategories] = React.useState<Set<PostCategory>>(new Set());
  const [sondaggiOnly, setSondaggiOnly] = React.useState(false);
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

  // Deep link: /?post=<id> (e.g. from a notification) opens that post's thread.
  React.useEffect(() => {
    const raw = new URLSearchParams(window.location.search).get("post");
    if (raw && /^\d+$/.test(raw)) setDetailPostId(Number(raw));
  }, []);

  const matchesFilter = React.useCallback(
    (p: Post) =>
      (categories.size === 0 || categories.has(p.category)) &&
      (!sondaggiOnly || p.post_type === "sondaggio"),
    [categories, sondaggiOnly],
  );

  const toggleCategory = React.useCallback((c: PostCategory) => {
    setCategories((prev) => {
      const next = new Set(prev);
      if (next.has(c)) next.delete(c);
      else next.add(c);
      return next;
    });
  }, []);

  const load = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const page = await api.listPosts({
        categories: categories.size ? [...categories] : undefined,
        postType: sondaggiOnly ? "sondaggio" : undefined,
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
  }, [categories, sondaggiOnly, t]);

  React.useEffect(() => {
    void load();
  }, [load]);

  const loadMore = React.useCallback(async () => {
    if (loading || loadingMore || !hasMore || cursor == null) return;
    setLoadingMore(true);
    try {
      const page = await api.listPosts({
        categories: categories.size ? [...categories] : undefined,
        postType: sondaggiOnly ? "sondaggio" : undefined,
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
  }, [loading, loadingMore, hasMore, cursor, categories, sondaggiOnly]);

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
          if (!matchesFilter(incoming)) return prev;
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
            .filter(matchesFilter),
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
      case "post.poll_vote": {
        const counts = new Map(event.data.options.map((o) => [o.id, o.vote_count]));
        setPosts((prev) =>
          prev.map((p) =>
            p.id === event.data.post_id
              ? {
                  ...p,
                  // Counts are authoritative; keep this viewer's own voted flags.
                  poll_options: p.poll_options.map((o) => ({
                    ...o,
                    vote_count: counts.get(o.id) ?? o.vote_count,
                  })),
                }
              : p,
          ),
        );
        break;
      }
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

  function handlePoll(post: Post, options: PollOption[]) {
    patchPost(post.id, { poll_options: options });
  }

  async function handleSubmit(values: PostFormValues) {
    const body = {
      title: values.title || null,
      content: values.content,
      category: values.category,
      post_type: values.postType,
      max_participants: values.maxParticipants,
      poll_mode: values.pollMode,
      poll_multi: values.pollMulti,
      options: values.options,
      participate: values.participate,
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
        prev.map((p) => (p.id === updated.id ? { ...p, ...updated } : p)).filter(matchesFilter),
      );
    } else {
      const created = await api.createPost(body);
      // De-dupe: the WebSocket "post.created" echo may already have added it.
      if (matchesFilter(created)) {
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
          <SectionHeading label={t("bacheca.label")} desc={t("bacheca.desc")} />
          <Button
            onClick={() => {
              setEditing(null);
              setFormOpen(true);
            }}
          >
            <Plus className="h-4 w-4" /> {t("bacheca.newMessage")}
          </Button>
        </div>

        <div className="mb-5">
          <CategoryPills
            selected={categories}
            onToggle={toggleCategory}
            onClear={() => setCategories(new Set())}
            trailing={
              <button
                type="button"
                aria-pressed={sondaggiOnly}
                onClick={() => setSondaggiOnly((v) => !v)}
                className={cn(
                  "border px-3 py-1.5 font-mono text-xs transition-colors",
                  sondaggiOnly
                    ? "border-[var(--border)] bg-[var(--primary)] text-[var(--primary-fg)] retro-shadow-sm"
                    : "border-[var(--border)] bg-[var(--surface)] text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--surface-2)]",
                )}
              >
                {t("cat.sondaggi")}
              </button>
            }
          />
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
            <Button variant="outline" size="sm" className="mt-3" onClick={() => void load()}>
              {t("common.retry")}
            </Button>
          </div>
        ) : posts.length === 0 ? (
          <div className="window retro-shadow p-8 text-center">
            <p className="font-display text-lg">{t("bacheca.emptyTitle")}</p>
            <p className="mt-1 font-mono text-sm text-[var(--text-muted)]">
              {t("bacheca.emptyHintPost")}
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
                  onPoll={handlePoll}
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

      <Sidebar
        className="order-1 lg:order-2"
        onOpenPost={(id) => setDetailPostId(id)}
        onShowSondaggi={() => {
          setSondaggiOnly(true);
          window.scrollTo({ top: 0, behavior: "smooth" });
        }}
      />

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
