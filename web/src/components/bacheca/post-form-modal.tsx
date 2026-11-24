"use client";

import * as React from "react";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import { Plus, X } from "lucide-react";

import { DialogContent } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input, Textarea } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { CATEGORIES } from "@/lib/categories";
import { useI18n } from "@/providers/i18n-provider";
import type { PollMode, Post, PostCategory, PostType } from "@/lib/types";

export interface PostFormValues {
  title: string;
  content: string;
  category: PostCategory;
  postType: PostType;
  maxParticipants: number | null;
  pollMode: PollMode;
  pollMulti: boolean;
  options: string[];
  participate: boolean;
}

const CERCO_TEAM_CHOICES = [1, 2, 3] as const;
const MAX_OPTIONS = 10;

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
  const [pollMode, setPollMode] = React.useState<PollMode>("attendance");
  const [options, setOptions] = React.useState<string[]>(["", ""]);
  const [pollMulti, setPollMulti] = React.useState(false);
  const [participate, setParticipate] = React.useState(true);
  const [submitting, setSubmitting] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const { t } = useI18n();

  const isEditing = editing != null;
  const isSondaggio = postType === "sondaggio";
  const isOptions = isSondaggio && pollMode === "options";
  const isAttendance = isSondaggio && pollMode === "attendance";
  const isCercoTeam = category === "cerco_team";
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
      setPollMode(editing?.poll_mode ?? "attendance");
      setPollMulti(editing?.poll_multi ?? false);
      setOptions(
        editing?.poll_options?.length ? editing.poll_options.map((o) => o.text) : ["", ""],
      );
      setParticipate(true);
      setError(null);
    }
  }, [open, editing]);

  function computeMaxParticipants(): number | null {
    if (postType === "post" || isOptions) return null;
    if (isCercoTeam) return cercoMax;
    return capMode === "unlimited" ? null : Math.max(1, customMax);
  }

  function updateOption(i: number, value: string) {
    setOptions((prev) => prev.map((o, idx) => (idx === i ? value : o)));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!content.trim()) {
      setError(t("postForm.errEmpty"));
      return;
    }
    const trimmedOptions = options.map((o) => o.trim()).filter(Boolean);
    if (isOptions && !isEditing) {
      const distinct = new Set(trimmedOptions.map((o) => o.toLowerCase()));
      if (trimmedOptions.length < 2 || distinct.size < 2) {
        setError(t("postForm.errOptions"));
        return;
      }
    }
    if (isAttendance) {
      const maxp = computeMaxParticipants();
      if (maxp != null && maxp < minParticipants) {
        setError(t("postForm.errBelow", { n: minParticipants }));
        return;
      }
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
        pollMode: isSondaggio ? pollMode : "attendance",
        pollMulti: isOptions ? pollMulti : false,
        options: isOptions && !isEditing ? trimmedOptions : [],
        participate: isAttendance ? participate : true,
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

          {/* Poll-mode selector — only when creating a sondaggio. */}
          {isSondaggio && !isEditing && (
            <div>
              <label className="mb-1 block font-mono text-xs text-[var(--text-muted)]">
                {t("postForm.pollModeLabel")}
              </label>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setPollMode("attendance")}
                  aria-pressed={pollMode === "attendance"}
                  className={chipClass(pollMode === "attendance")}
                >
                  {t("postForm.pollAttendance")}
                </button>
                <button
                  type="button"
                  onClick={() => setPollMode("options")}
                  aria-pressed={pollMode === "options"}
                  className={chipClass(pollMode === "options")}
                >
                  {t("postForm.pollOptions")}
                </button>
              </div>
            </div>
          )}

          {/* Options editor (create only). */}
          {isOptions && !isEditing && (
            <div className="border border-dashed border-[var(--border)] p-3">
              <label className="mb-2 block font-mono text-xs text-[var(--text-muted)]">
                {t("postForm.optionsLabel")}
              </label>
              <div className="flex flex-col gap-2">
                {options.map((opt, i) => (
                  <div key={i} className="flex items-center gap-2">
                    <Input
                      value={opt}
                      onChange={(e) => updateOption(i, e.target.value)}
                      maxLength={120}
                      placeholder={t("postForm.optionPlaceholder", { n: i + 1 })}
                    />
                    {options.length > 2 && (
                      <button
                        type="button"
                        onClick={() => setOptions((prev) => prev.filter((_, idx) => idx !== i))}
                        aria-label={t("postForm.removeOption")}
                        className="shrink-0 border border-[var(--border)] bg-[var(--surface)] p-1.5 text-[var(--text-muted)] hover:text-[var(--text)]"
                      >
                        <X className="h-3.5 w-3.5" />
                      </button>
                    )}
                  </div>
                ))}
              </div>
              {options.length < MAX_OPTIONS && (
                <button
                  type="button"
                  onClick={() => setOptions((prev) => [...prev, ""])}
                  className="mt-2 inline-flex items-center gap-1 font-mono text-xs text-[var(--primary)] hover:underline"
                >
                  <Plus className="h-3.5 w-3.5" /> {t("postForm.addOption")}
                </button>
              )}
              <label className="mt-3 flex cursor-pointer items-center gap-2 font-mono text-xs">
                <input
                  type="checkbox"
                  checked={pollMulti}
                  onChange={(e) => setPollMulti(e.target.checked)}
                  className="h-3.5 w-3.5 accent-[var(--primary)]"
                />
                {t("postForm.multiLabel")}
              </label>
            </div>
          )}

          {isOptions && isEditing && (
            <p className="font-mono text-[11px] text-[var(--text-muted)]">
              {t("postForm.optionsLocked")}
            </p>
          )}

          {/* Capacity — attendance sondaggio only, on create and edit. */}
          {isAttendance && (
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
                      onChange={(e) => setCustomMax(Math.max(1, Number(e.target.value) || 1))}
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
              {!isEditing && (
                <label className="mt-3 flex cursor-pointer items-center gap-2 font-mono text-xs">
                  <input
                    type="checkbox"
                    checked={participate}
                    onChange={(e) => setParticipate(e.target.checked)}
                    className="h-3.5 w-3.5 accent-[var(--primary)]"
                  />
                  {t("postForm.participateLabel")}
                </label>
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
