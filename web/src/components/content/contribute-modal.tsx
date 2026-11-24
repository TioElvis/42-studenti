"use client";

import * as React from "react";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import { ExternalLink, Upload } from "lucide-react";

import { DialogContent } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input, Textarea } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { api, ApiError } from "@/lib/api";
import { useI18n } from "@/providers/i18n-provider";
import type { ContentSection } from "@/lib/types";

/** Contribute a file to assets/<section>/ as a fork-based GitHub PR. */
export function ContributeModal({
  open,
  onOpenChange,
  section,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  section: ContentSection;
}) {
  const { t } = useI18n();
  const [mode, setMode] = React.useState<"text" | "file">("text");
  const [folder, setFolder] = React.useState("");
  const [filename, setFilename] = React.useState("");
  const [text, setText] = React.useState("");
  const [b64, setB64] = React.useState("");
  const [message, setMessage] = React.useState("");
  const [submitting, setSubmitting] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [prUrl, setPrUrl] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (open) {
      setMode("text");
      setFolder("");
      setFilename("");
      setText("");
      setB64("");
      setMessage("");
      setError(null);
      setPrUrl(null);
    }
  }, [open]);

  function onFile(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    if (!f) return;
    const reader = new FileReader();
    reader.onload = () => {
      const result = typeof reader.result === "string" ? reader.result : "";
      setB64(result.split(",")[1] ?? "");
      setFilename(f.name);
    };
    reader.readAsDataURL(f);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const name = filename.trim();
    if (!name) {
      setError(t("contribute.errName"));
      return;
    }
    if (mode === "text" && !text.trim()) {
      setError(t("contribute.errContent"));
      return;
    }
    if (mode === "file" && !b64) {
      setError(t("contribute.errFile"));
      return;
    }
    const cleanFolder = folder.trim().replace(/^\/+|\/+$/g, "");
    const path = cleanFolder ? `${cleanFolder}/${name}` : name;
    setSubmitting(true);
    setError(null);
    try {
      const res = await api.contributeContent({
        section,
        path,
        content: mode === "text" ? text : b64,
        encoding: mode === "text" ? "utf-8" : "base64",
        message: message.trim() || null,
      });
      setPrUrl(res.pr_url);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("contribute.errGeneric"));
    } finally {
      setSubmitting(false);
    }
  }

  const chip = (active: boolean) =>
    cn(
      "border px-2.5 py-1 font-mono text-xs transition-colors",
      active
        ? "border-[var(--ring)] bg-[var(--surface-2)]"
        : "border-[var(--border)] bg-[var(--surface)] text-[var(--text-muted)] hover:text-[var(--text)]",
    );

  return (
    <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
      <DialogContent title={t("contribute.title")} barTitle={t("contribute.bar")}>
        {prUrl ? (
          <div className="flex flex-col gap-3">
            <p className="font-display text-lg">{t("contribute.successTitle")}</p>
            <p className="font-mono text-sm text-[var(--text-muted)]">
              {t("contribute.successBody")}
            </p>
            <Button asChild>
              <a href={prUrl} target="_blank" rel="noopener noreferrer">
                <ExternalLink className="h-4 w-4" /> {t("contribute.viewPr")}
              </a>
            </Button>
            <Button variant="outline" onClick={() => setPrUrl(null)}>
              {t("contribute.another")}
            </Button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setMode("text")}
                aria-pressed={mode === "text"}
                className={chip(mode === "text")}
              >
                {t("contribute.modeText")}
              </button>
              <button
                type="button"
                onClick={() => setMode("file")}
                aria-pressed={mode === "file"}
                className={chip(mode === "file")}
              >
                {t("contribute.modeFile")}
              </button>
            </div>

            <div>
              <label className="mb-1 block font-mono text-xs text-[var(--text-muted)]">
                {t("contribute.folderLabel")}
              </label>
              <Input
                value={folder}
                onChange={(e) => setFolder(e.target.value)}
                placeholder={t("contribute.folderPlaceholder")}
                maxLength={200}
              />
            </div>

            {mode === "text" ? (
              <>
                <div>
                  <label className="mb-1 block font-mono text-xs text-[var(--text-muted)]">
                    {t("contribute.filenameLabel")}
                  </label>
                  <Input
                    value={filename}
                    onChange={(e) => setFilename(e.target.value)}
                    placeholder={t("contribute.filenamePlaceholder")}
                    maxLength={120}
                  />
                </div>
                <div>
                  <label className="mb-1 block font-mono text-xs text-[var(--text-muted)]">
                    {t("contribute.contentLabel")}
                  </label>
                  <Textarea
                    value={text}
                    onChange={(e) => setText(e.target.value)}
                    rows={8}
                    placeholder={t("contribute.contentPlaceholder")}
                  />
                </div>
              </>
            ) : (
              <div>
                <label className="mb-1 block font-mono text-xs text-[var(--text-muted)]">
                  {t("contribute.fileLabel")}
                </label>
                <label className="flex cursor-pointer items-center gap-2 border border-dashed border-[var(--border)] bg-[var(--surface)] px-3 py-3 font-mono text-xs hover:bg-[var(--surface-2)]">
                  <Upload className="h-4 w-4" />
                  <span className="truncate">{filename || t("contribute.fileLabel")}</span>
                  <input type="file" onChange={onFile} className="sr-only" />
                </label>
              </div>
            )}

            <div>
              <label className="mb-1 block font-mono text-xs text-[var(--text-muted)]">
                {t("contribute.messageLabel")}
              </label>
              <Input
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                maxLength={200}
              />
            </div>

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
                {submitting ? t("contribute.submitting") : t("contribute.submit")}
              </Button>
            </div>
          </form>
        )}
      </DialogContent>
    </DialogPrimitive.Root>
  );
}
