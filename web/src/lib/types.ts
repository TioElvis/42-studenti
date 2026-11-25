/** Shared API types, mirroring the FastAPI response schemas. */

export type PostCategory =
  | "studio"
  | "cerco_team"
  | "evento_casuale"
  | "mercatino"
  | "off_topic";

export type PostType = "post" | "sondaggio";

export type PollMode = "attendance" | "options";

export interface PollOption {
  id: number;
  text: string;
  vote_count: number;
  voted_by_me: boolean;
}

export interface PollState {
  post_id: number;
  options: PollOption[];
}

export interface UserPublic {
  id: number;
  login: string;
  display_name: string | null;
  avatar_url: string | null;
  campus: string | null;
}

export interface UserMe extends UserPublic {
  email: string | null;
  intra_id: number;
}

export interface Comment {
  id: number;
  content: string;
  created_at: string;
  author: UserPublic;
  is_mine: boolean;
  parent_id: number | null;
  /** Login of the user this comment replies to (for the @ref); null if none. */
  reply_to: string | null;
}

export interface Post {
  id: number;
  title: string | null;
  content: string;
  category: PostCategory;
  post_type: PostType;
  max_participants: number | null;
  poll_mode: PollMode;
  poll_multi: boolean;
  poll_options: PollOption[];
  created_at: string;
  updated_at: string;
  author: UserPublic;
  like_count: number;
  comment_count: number;
  liked_by_me: boolean;
  is_mine: boolean;
  rsvp_count: number;
  rsvp_full: boolean;
  joined_by_me: boolean;
}

export interface PostDetail extends Post {
  comments: Comment[];
}

export interface PostPage {
  items: Post[];
  next_cursor: number | null;
}

export interface LikeState {
  liked: boolean;
  like_count: number;
}

export interface RsvpState {
  joined: boolean;
  rsvp_count: number;
  rsvp_full: boolean;
}

/** Live events pushed over the WebSocket (mirror of the backend broadcasts). */
export type RealtimeEvent =
  | { type: "post.created"; data: PostDetail }
  | { type: "post.updated"; data: PostDetail }
  | { type: "post.deleted"; data: { id: number } }
  | { type: "post.like"; data: { post_id: number; like_count: number } }
  | {
      type: "comment.created";
      data: { post_id: number; comment_count: number; comment: Comment };
    }
  | {
      type: "comment.deleted";
      data: { post_id: number; comment_id: number; comment_count: number };
    }
  | { type: "event.interest"; data: { event_id: number; interest_count: number } }
  | {
      type: "post.rsvp";
      data: { post_id: number; rsvp_count: number; rsvp_full: boolean };
    }
  | {
      type: "post.poll_vote";
      data: { post_id: number; options: { id: number; vote_count: number }[] };
    };

export interface EventItem {
  id: number;
  name: string | null;
  description: string | null;
  location: string | null;
  kind: string | null;
  begin_at: string | null;
  end_at: string | null;
  max_people: number | null;
  nbr_subscribers: number | null;
  internal: boolean;
  interested: boolean;
  interest_count: number;
}

/** A student registered to an event, as reported live by the 42 API. */
export interface EventAttendee {
  login: string;
  display_name: string | null;
  avatar_url: string | null;
}

/** One page of the Studenti directory. */
export interface StudentPage {
  items: UserPublic[];
  total: number;
  page: number;
  pages: number;
}

export interface InterestState {
  interested: boolean;
  interest_count: number;
}

/** File-based Materiale / Archivio content (served from assets/). */
export type ContentSection = "material" | "archive";

export type ContentKind = "text" | "image" | "pdf" | "other";

export interface ContentEntry {
  path: string; // e.g. "exam02/help.md"
  name: string; // e.g. "help.md"
  folder: string; // parent folder relative to the section root ("" at root)
  size: number;
  kind: ContentKind;
  mime: string;
  sha: string; // git blob sha (metadata only)
  github_url: string; // github.com blob URL
  raw_url: string; // raw.githubusercontent.com URL
}

export interface ContentList {
  section: ContentSection;
  entries: ContentEntry[];
  folders: string[]; // every folder path, including empty (.gitkeep-only) ones
}

export interface ContributeResult {
  url: string;
  action: "created" | "updated";
}

export interface ContentFile {
  path: string;
  name: string;
  content: string;
}

export interface GithubStatus {
  configured: boolean;
  server_mode: boolean;
  linked: boolean;
  username: string | null;
  can_archive: boolean; // special user: may upload to the archive
  can_delete: boolean; // special user: may delete files/folders
}

export interface ActivityStats {
  posts: number;
  comments: number;
  daje_received: number;
  rsvps: number;
  logins: number;
}

export interface ProjectInfo {
  name: string;
  status: string;
  mark: number | null;
  validated: boolean | null;
}

export interface Intra42Info {
  level: number | null;
  grade: string | null;
  correction_point: number | null;
  wallet: number | null;
  location: string | null;
  pool: string | null;
  joined: string | null;
  projects: ProjectInfo[];
  achievements: string[];
}

export type NotificationKind = "post" | "comment" | "reply" | "follow";

export interface AppNotification {
  id: number;
  type: NotificationKind;
  actor: UserPublic;
  post_id: number | null;
  is_read: boolean;
  created_at: string;
}

export interface NotificationPage {
  items: AppNotification[];
  next_cursor: number | null;
  unread: number;
}

export type NotificationFilter = "all" | "posts" | "comments" | "follows";

export type PostNotify = "off" | "followed" | "all";

export interface NotificationSettings {
  notify_posts: PostNotify;
  notify_comments: boolean;
  notify_follows: boolean;
}

export interface Profile {
  login: string;
  display_name: string | null;
  avatar_url: string | null;
  campus: string | null;
  is_me: boolean;
  activity: ActivityStats;
  intra: Intra42Info;
  followers: number;
  following: number;
  is_following: boolean;
  followable: boolean;
}
