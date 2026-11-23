"use client";

import * as React from "react";
import Link from "next/link";
import { CornerDownRight, Reply, Trash2, X } from "lucide-react";

import { Avatar } from "@/components/chrome/avatar";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/input";
import { Linkify } from "@/components/ui/linkify";
import { relativeTime } from "@/lib/time";
import { api } from "@/lib/api";
import { useI18n } from "@/providers/i18n-provider";
import type { Comment } from "@/lib/types";

export function CommentList({
  postId,
  comments,
  onAdd,
  onDelete,
}: {
  postId: number;
  comments: Comment[];
  onAdd: (comment: Comment) => void;
  onDelete: (commentId: number) => void;
}) {
  const { t, lang } = useI18n();
  const [text, setText] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [replyTo, setReplyTo] = React.useState<Comment | null>(null);
  const textareaRef = React.useRef<HTMLTextAreaElement | null>(null);

  function startReply(comment: Comment) {
    setReplyTo(comment);
    // Let the banner render, then focus the composer.
    requestAnimationFrame(() => textareaRef.current?.focus());
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!text.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const created = await api.addComment(postId, text.trim(), replyTo?.id ?? null);
      onAdd(created);
      setText("");
      setReplyTo(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("comments.errSend"));
    } finally {
      setBusy(false);
    }
  }

  async function remove(id: number) {
    try {
      await api.deleteComment(id);
      onDelete(id);
    } catch {
      /* keep it; a transient failure shouldn't drop the comment from view */
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="font-mono text-xs uppercase tracking-wide text-[var(--text-muted)]">
        {t("comments.title", { n: comments.length })}
      </div>

      {comments.length === 0 ? (
        <p className="border border-dashed border-[var(--border)] p-3 text-center font-mono text-xs text-[var(--text-muted)]">
          {t("comments.empty")}
        </p>
      ) : (
        <ul className="flex flex-col gap-2.5">
          {comments.map((c) => (
            <li
              key={c.id}
              className="border border-[var(--border)] bg-[var(--surface-sunken)] p-3"
            >
              <div className="mb-1 flex items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <Avatar user={c.author} size={22} />
                  <Link
                    href={`/u/${c.author.login}`}
                    className="font-mono text-xs font-bold hover:underline"
                  >
                    @{c.author.login}
                  </Link>
                  <span className="font-mono text-[11px] text-[var(--text-muted)]">
                    {relativeTime(c.created_at, lang)}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    aria-label={t("comments.replyTo", { login: c.author.login })}
                    onClick={() => startReply(c)}
                    className="text-[var(--text-muted)] hover:text-[var(--primary)]"
                  >
                    <Reply className="h-3.5 w-3.5" />
                  </button>
                  {c.is_mine && (
                    <button
                      type="button"
                      aria-label={t("comments.deleteComment")}
                      onClick={() => void remove(c.id)}
                      className="text-[var(--text-muted)] hover:text-[var(--primary)]"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  )}
                </div>
              </div>
              {c.reply_to && (
                <div className="mb-1 flex items-center gap-1 font-mono text-[11px] text-[var(--text-muted)]">
                  <CornerDownRight className="h-3 w-3" aria-hidden />
                  {t("comments.inReplyTo")} <span className="font-bold">@{c.reply_to}</span>
                </div>
              )}
              <p className="whitespace-pre-wrap break-words text-sm">
                <Linkify>{c.content}</Linkify>
              </p>
            </li>
          ))}
        </ul>
      )}

      <form onSubmit={submit} className="flex flex-col gap-2">
        {replyTo && (
          <div className="flex items-center justify-between gap-2 border border-[var(--border-subtle)] bg-[var(--surface-2)] px-2.5 py-1.5 font-mono text-[11px]">
            <span className="flex items-center gap-1 text-[var(--text-muted)]">
              <Reply className="h-3 w-3" aria-hidden /> {t("comments.replyBanner")}{" "}
              <span className="font-bold text-[var(--text)]">@{replyTo.author.login}</span>
            </span>
            <button
              type="button"
              aria-label={t("comments.cancelReply")}
              onClick={() => setReplyTo(null)}
              className="text-[var(--text-muted)] hover:text-[var(--primary)]"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        )}
        <Textarea
          ref={textareaRef}
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={2}
          maxLength={2000}
          placeholder={
            replyTo
              ? t("comments.replyPlaceholder", { login: replyTo.author.login })
              : t("comments.placeholder")
          }
        />
        {error && (
          <p className="font-mono text-xs text-[var(--primary)]" role="alert">
            {error}
          </p>
        )}
        <div className="flex justify-end">
          <Button type="submit" size="sm" disabled={busy || !text.trim()}>
            {busy ? t("common.sending") : replyTo ? t("comments.submitReply") : t("comments.submit")}
          </Button>
        </div>
      </form>
    </div>
  );
}
