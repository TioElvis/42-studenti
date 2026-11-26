/** Thin client for the FastAPI backend.
 *
 * Auth is cookie-based (httpOnly session cookie set by the backend), so every
 * request sends credentials. The 42 access token never reaches this code.
 */

import type {
  Comment,
  EventItem,
  InterestState,
  LikeState,
  PostCategory,
  ContentFile,
  ContentList,
  ContentSection,
  EventAttendee,
  StudentPage,
  StudentStats,
  ContributeResult,
  GithubStatus,
  NotificationFilter,
  NotificationPage,
  NotificationSettings,
  PollMode,
  PollState,
  PostDetail,
  Profile,
  PostPage,
  PostType,
  PushSubscriptionBody,
  RsvpState,
  UserMe,
  UserPublic,
} from "./types";

const API_BASE = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:9000").replace(/\/$/, "");

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    credentials: "include",
    headers: {
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
      ...init?.headers,
    },
  });

  if (res.status === 204) {
    return undefined as T;
  }

  let data: unknown = null;
  const text = await res.text();
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }
  }

  if (!res.ok) {
    const detail =
      (data && typeof data === "object" && "detail" in data
        ? String((data as { detail: unknown }).detail)
        : null) ?? `Errore ${res.status}`;
    throw new ApiError(res.status, detail);
  }

  return data as T;
}

/** Absolute URL to begin the 42 OAuth login (full-page navigation). */
export function loginUrl(): string {
  return `${API_BASE}/auth/42`;
}

/** Absolute URL to begin linking a GitHub account (full-page navigation). */
export function githubLinkUrl(): string {
  return `${API_BASE}/github/link`;
}

export const api = {
  // A hung connection to a sleeping API must not block forever: abort after 25 s
  // (the caller then treats it like "API waking up").
  me: () => request<UserMe>("/me", { signal: AbortSignal.timeout(25_000) }),
  /** Cheap liveness probe: true once the API answers (used while it wakes up). */
  health: async (): Promise<boolean> => {
    try {
      const res = await fetch(`${API_BASE}/health`, {
        cache: "no-store",
        signal: AbortSignal.timeout(8_000),
      });
      return res.ok;
    } catch {
      return false;
    }
  },
  logout: () => request<{ detail: string }>("/auth/logout", { method: "POST" }),

  listPosts: (
    opts: {
      categories?: PostCategory[];
      postType?: PostType;
      q?: string;
      cursor?: number | null;
      limit?: number;
    } = {},
  ) => {
    const p = new URLSearchParams();
    // Repeat ?category= for each selected category (any-of multi-select).
    opts.categories?.forEach((c) => p.append("category", c));
    if (opts.postType) p.set("post_type", opts.postType);
    if (opts.q) p.set("q", opts.q);
    if (opts.cursor != null) p.set("cursor", String(opts.cursor));
    if (opts.limit != null) p.set("limit", String(opts.limit));
    const qs = p.toString();
    return request<PostPage>(`/posts${qs ? `?${qs}` : ""}`);
  },
  getPost: (id: number) => request<PostDetail>(`/posts/${id}`),
  createPost: (body: {
    title?: string | null;
    content: string;
    category: PostCategory;
    post_type: PostType;
    max_participants?: number | null;
    poll_mode?: PollMode;
    poll_multi?: boolean;
    options?: string[];
    participate?: boolean;
  }) => request<PostDetail>("/posts", { method: "POST", body: JSON.stringify(body) }),
  updatePost: (
    id: number,
    body: {
      title?: string | null;
      content?: string;
      category?: PostCategory;
      max_participants?: number | null;
    },
  ) => request<PostDetail>(`/posts/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  deletePost: (id: number) => request<void>(`/posts/${id}`, { method: "DELETE" }),
  toggleLike: (id: number) => request<LikeState>(`/posts/${id}/like`, { method: "POST" }),
  toggleRsvp: (id: number) => request<RsvpState>(`/posts/${id}/rsvp`, { method: "POST" }),
  listAttendees: (id: number) => request<UserPublic[]>(`/posts/${id}/attendees`),
  votePoll: (postId: number, optionId: number) =>
    request<PollState>(`/posts/${postId}/poll/vote`, {
      method: "POST",
      body: JSON.stringify({ option_id: optionId }),
    }),

  addComment: (postId: number, content: string, parentId?: number | null) =>
    request<Comment>(`/posts/${postId}/comments`, {
      method: "POST",
      body: JSON.stringify({ content, parent_id: parentId ?? null }),
    }),
  deleteComment: (commentId: number) =>
    request<void>(`/comments/${commentId}`, { method: "DELETE" }),

  listEvents: () => request<EventItem[]>("/events"),
  eventAttendees: (eventId: number) =>
    request<EventAttendee[]>(`/events/${eventId}/attendees`),
  toggleEventInterest: (eventId: number) =>
    request<InterestState>(`/events/${eventId}/interest`, { method: "POST" }),

  // no-store: the listing must reflect a just-made commit (server cache is invalidated).
  listContent: (section: ContentSection) =>
    request<ContentList>(`/content/${section}`, { cache: "no-store" }),
  readContent: (section: ContentSection, path: string) =>
    request<ContentFile>(`/content/${section}/raw?path=${encodeURIComponent(path)}`),
  /** Absolute URL to stream a file (any type). ``download`` forces a download;
   * otherwise images/PDFs are served inline for in-page rendering. */
  contentFileUrl: (section: ContentSection, path: string, download = false) =>
    `${API_BASE}/content/${section}/file?path=${encodeURIComponent(path)}` +
    (download ? "&download=1" : ""),

  /** Own profile when `login` is omitted, otherwise another student's. */
  getProfile: (login?: string) =>
    request<Profile>(login ? `/profile/${encodeURIComponent(login)}` : "/profile"),

  studentsPage: (q: string, page: number, pageSize = 20) =>
    request<StudentPage>(
      `/students/page?q=${encodeURIComponent(q)}&page=${page}&page_size=${pageSize}`,
    ),
  studentStats: () => request<StudentStats>("/students/stats", { cache: "no-store" }),
  searchStudents: (q: string) =>
    request<UserPublic[]>(`/students?q=${encodeURIComponent(q)}`),

  followUser: (login: string) =>
    request<void>(`/users/${encodeURIComponent(login)}/follow`, { method: "POST" }),
  unfollowUser: (login: string) =>
    request<void>(`/users/${encodeURIComponent(login)}/follow`, { method: "DELETE" }),

  listNotifications: (opts: { cursor?: number | null; filter?: NotificationFilter } = {}) => {
    const p = new URLSearchParams();
    if (opts.cursor != null) p.set("cursor", String(opts.cursor));
    if (opts.filter && opts.filter !== "all") p.set("filter", opts.filter);
    const qs = p.toString();
    return request<NotificationPage>(`/notifications${qs ? `?${qs}` : ""}`);
  },
  unreadNotifications: () => request<{ unread: number }>("/notifications/unread-count"),
  markNotificationsRead: () => request<void>("/notifications/read-all", { method: "POST" }),
  getNotificationSettings: () => request<NotificationSettings>("/notifications/settings"),
  updateNotificationSettings: (body: Partial<NotificationSettings>) =>
    request<NotificationSettings>("/notifications/settings", {
      method: "PATCH",
      body: JSON.stringify(body),
    }),

  pushKey: () => request<{ public_key: string | null }>("/notifications/push/key"),
  pushSubscribe: (body: PushSubscriptionBody) =>
    request<void>("/notifications/push/subscribe", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  pushUnsubscribe: (endpoint: string) =>
    request<void>("/notifications/push/unsubscribe", {
      method: "POST",
      body: JSON.stringify({ endpoint }),
    }),

  githubStatus: () => request<GithubStatus>("/github/status"),
  unlinkGithub: () => request<void>("/github/link", { method: "DELETE" }),
  /** Delete a file, or a whole folder (one commit). Special users only. */
  deleteContent: (body: {
    section: ContentSection;
    path: string;
    folder?: boolean;
    message?: string | null;
  }) =>
    request<{ url: string; action: "deleted" }>("/github/delete", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  /** Commit a file (or, with `create_folder`, a `<folder>/.gitkeep`) straight to
   * the repo's main branch. Overwrites an existing file at the same path. */
  contributeContent: (body: {
    section: ContentSection;
    path: string;
    content?: string;
    encoding?: "utf-8" | "base64";
    message?: string | null;
    create_folder?: boolean;
  }) =>
    request<ContributeResult>("/github/contribute", {
      method: "POST",
      body: JSON.stringify(body),
    }),
};
