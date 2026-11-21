/** Shared API types, mirroring the FastAPI response schemas. */

export type PostCategory =
  | "studio"
  | "cerco_team"
  | "evento_casuale"
  | "vita_romana"
  | "mercatino"
  | "off_topic";

export type PostType = "post" | "sondaggio";

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
  interested: boolean;
  interest_count: number;
}

export interface InterestState {
  interested: boolean;
  interest_count: number;
}

/** File-based Materiale / Archivio content (served from assets/). */
export type ContentSection = "material" | "archive";

export interface ContentEntry {
  path: string; // e.g. "exam02/help.md"
  name: string; // e.g. "help.md"
  folder: string; // parent folder relative to the section root ("" at root)
  size: number;
  text: boolean;
}

export interface ContentList {
  section: ContentSection;
  entries: ContentEntry[];
}

export interface ContentFile {
  path: string;
  name: string;
  content: string;
}
