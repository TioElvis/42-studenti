"use client";

import * as React from "react";
import * as DialogPrimitive from "@radix-ui/react-dialog";

import { DialogContent } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input, Textarea } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { CATEGORIES } from "@/lib/categories";
import { useI18n } from "@/providers/i18n-provider";
import type { Post, PostCategory, PostType } from "@/lib/types";

export interface PostFormValues {
  title: string;
  content: string;
  category: PostCategory;
  postType: PostType;
  maxParticipants: number | null;
}

const CERCO_TEAM_CHOICES = [1, 2, 3] as const;

export function PostFormModal({
  open,
  onOpenChange,
  editing,
  onSubmit,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  editing: Post | null;
  onSubmit: (values: PostFormValues) => Promise<void>;
}) {
  const [title, setTitle] = React.useState("");
  const [content, setContent] = React.useState("");
  const [category, setCategory] = React.useState<PostCategory>("studio");
  const [postType, setPostType] = React.useState<PostType>("post");
  const [cercoMax, setCercoMax] = React.useState(2);
  const [capMode, setCapMode] = React.useState<"unlimited" | "custom">("unlimited");
  const [customMax, setCustomMax] = React.useState(5);
  const [submitting, setSubmitting] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const { t } = useI18n();

  const isEditing = editing != null;
  const isSondaggio = postType === "sondaggio";
  const isCercoTeam = category === "cerco_team";
  // When editing, capacity may not be lowered below the confirmed attendees.
  const minParticipants = isEditing ? (editing?.rsvp_count ?? 0) : 0;

  React.useEffect(() => {
    if (open) {
      setTitle(editing?.title ?? "");
      setContent(editing?.content ?? "");
      setCategory(editing?.category ?? "studio");
      setPostType(editing?.post_type ?? "post");
      setCercoMax(editing?.max_participants ?? 2);
      setCapMode(editing?.max_participants == null ? "unlimited" : "custom");
      setCustomMax(editing?.max_participants ?? 5);
      setError(null);
    }
  }, [open, editing]);

  function computeMaxParticipants(): number | null {
    if (postType === "post") return null;
    if (isCercoTeam) return cercoMax;
    return capMode === "unlimited" ? null : Math.max(1, customMax);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!content.trim()) {
      setError(t("postForm.errEmpty"));
      return;
    }
    const maxp = computeMaxParticipants();
    if (isSondaggio && maxp != null && maxp < minParticipants) {
      setError(t("postForm.errBelow", { n: minParticipants }));
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await onSubmit({
        title: title.trim(),
        content: content.trim(),
        category,
        postType,
        maxParticipants: computeMaxParticipants(),
      });
      onOpenChange(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("postForm.errGeneric"));
    } finally {
      setSubmitting(false);
    }
  }

  const chipClass = (active: boolean) =>
    cn(
      "border px-2.5 py-1 font-mono text-xs transition-colors",
      active
        ? "border-[var(--ring)] bg-[var(--surface-2)]"
        : "border-[var(--border)] bg-[var(--surface)] text-[var(--text-muted)] hover:text-[var(--text)]",
    );

  return (
    <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
      <DialogContent
        title={isEditing ? t("postForm.titleEdit") : t("postForm.titleNew")}
        barTitle={isEditing ? t("postForm.barEdit") : t("postForm.barNew")}
      >
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          {/* Type selector — only when creating (type is fixed after creation). */}
          {!isEditing && (
            <div>
              <label className="mb-1 block font-mono text-xs text-[var(--text-muted)]">
                {t("postForm.typeLabel")}
              </label>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setPostType("post")}
                  aria-pressed={!isSondaggio}
                  className={chipClass(!isSondaggio)}
                >
                  {t("postForm.typePost")}
                </button>
                <button
                  type="button"
                  onClick={() => setPostType("sondaggio")}
                  aria-pressed={isSondaggio}
                  title={t("postForm.typeSondaggioTitle")}
                  className={chipClass(isSondaggio)}
                >
                  {t("postForm.typeSondaggio")}
                </button>
              </div>
            </div>
          )}

          <div>
            <label className="mb-1 block font-mono text-xs text-[var(--text-muted)]">
              {t("postForm.titleLabel")}
            </label>
            <Input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              maxLength={140}
              placeholder={t("postForm.titlePlaceholder")}
            />
          </div>

          <div>
            <label className="mb-1 block font-mono text-xs text-[var(--text-muted)]">
              {t("postForm.msgLabel")}
            </label>
            <Textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              maxLength={4000}
              rows={5}
              placeholder={t("postForm.msgPlaceholder")}
              required
            />
          </div>

          <div>
            <label className="mb-1 block font-mono text-xs text-[var(--text-muted)]">
              {t("postForm.categoryLabel")}
            </label>
            <div className="flex flex-wrap gap-2">
              {CATEGORIES.map((c) => (
                <button
                  key={c.slug}
                  type="button"
                  onClick={() => setCategory(c.slug)}
                  aria-pressed={category === c.slug}
                  title={t(`catHint.${c.slug}`)}
                  className={chipClass(category === c.slug)}
                >
                  {t(`cat.${c.slug}`)}
                </button>
              ))}
            </div>
          </div>

          {/* Capacity — shown for a sondaggio, on create and on edit. */}
          {isSondaggio && (
            <div className="border border-dashed border-[var(--border)] p-3">
              <label className="mb-2 block font-mono text-xs text-[var(--text-muted)]">
                {isCercoTeam ? t("postForm.capCercoLabel") : t("postForm.capSpotsLabel")}
              </label>
              {isCercoTeam ? (
                <div className="flex gap-2">
                  {CERCO_TEAM_CHOICES.map((n) => (
                    <button
                      key={n}
                      type="button"
                      onClick={() => setCercoMax(n)}
                      disabled={n < minParticipants}
                      aria-pressed={cercoMax === n}
                      className={cn(chipClass(cercoMax === n), n < minParticipants && "opacity-40")}
                    >
                      {n}
                    </button>
                  ))}
                </div>
              ) : (
                <div className="flex flex-wrap items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setCapMode("unlimited")}
                    aria-pressed={capMode === "unlimited"}
                    className={chipClass(capMode === "unlimited")}
                  >
                    {t("postForm.unlimited")}
                  </button>
                  <button
                    type="button"
                    onClick={() => setCapMode("custom")}
                    aria-pressed={capMode === "custom"}
                    className={chipClass(capMode === "custom")}
                  >
                    {t("postForm.number")}
                  </button>
                  {capMode === "custom" && (
                    <Input
                      type="number"
                      min={Math.max(1, minParticipants)}
                      max={500}
                      value={customMax}
                      onChange={(e) =>
                        setCustomMax(Math.max(1, Number(e.target.value) || 1))
                      }
                      className="w-24"
                      aria-label={t("postForm.maxAria")}
                    />
                  )}
                </div>
              )}
              {minParticipants > 0 && (
                <p className="mt-2 font-mono text-[11px] text-[var(--text-muted)]">
                  {t("postForm.alreadyN", { n: minParticipants })}
                </p>
              )}
            </div>
          )}

          {error && (
            <p className="font-mono text-xs text-[var(--primary)]" role="alert">
              {error}
            </p>
          )}

          <div className="flex justify-end gap-2">
            <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>
              {t("common.cancel")}
            </Button>
            <Button type="submit" disabled={submitting}>
              {submitting ? t("common.sending") : isEditing ? t("common.save") : t("common.publish")}
            </Button>
          </div>
        </form>
      </DialogContent>
    </DialogPrimitive.Root>
  );
}
