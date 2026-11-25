"use client";

import * as React from "react";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import { Upload } from "lucide-react";

import { DialogContent } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input, Textarea } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { api, ApiError } from "@/lib/api";
import { useI18n } from "@/providers/i18n-provider";
import type { ContentSection, ContributeResult } from "@/lib/types";

/** Mirror of the server rules: no empty / `.` / `..` segments, no backslash,
 * no leading or trailing slash. (The server re-validates everything.) */
function validPath(p: string): boolean {
  if (!p || p.includes("\\") || p.startsWith("/") || p.endsWith("/")) return false;
  return p.split("/").every((seg) => seg !== "" && seg !== "." && seg !== ".." && !seg.startsWith("."));
}

function joinPath(...parts: string[]): string {
  return parts.filter(Boolean).join("/");
}

/** Commit a file (or an empty folder) straight to assets/<section>/ on GitHub.
 * Same folder + filename as an existing file → that file is updated. */
export function ContributeModal({
  open,
  onOpenChange,
  section,
  intent = "upload",
  initialFolder = "",
  folders,
  existingPaths,
  onDone,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  section: ContentSection;
  /** "upload" adds/updates a file; "folder" creates an (empty) folder. */
  intent?: "upload" | "folder";
  /** Folder preselected as the upload target ("" = section root). */
  initialFolder?: string;
  /** Existing folders of the section (for the picker). */
  folders: string[];
  /** Paths of existing files (to tell "uploading" from "updating"). */
  existingPaths: ReadonlySet<string>;
  /** Called after a successful commit so the caller can reload the listing. */
  onDone?: () => void;
}) {
  const { t } = useI18n();
  const isFolderIntent = intent === "folder";
  const [mode, setMode] = React.useState<"text" | "file">("text");
  const [folder, setFolder] = React.useState("");
  const [newFolder, setNewFolder] = React.useState("");
  const [filename, setFilename] = React.useState("");
  const [text, setText] = React.useState("");
  const [b64, setB64] = React.useState("");
  const [message, setMessage] = React.useState("");
  const [submitting, setSubmitting] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [result, setResult] = React.useState<ContributeResult | null>(null);

  React.useEffect(() => {
    if (open) {
      setMode("text");
      setFolder(initialFolder);
      setNewFolder("");
      setFilename("");
      setText("");
      setB64("");
      setMessage("");
      setError(null);
      setResult(null);
    }
  }, [open, initialFolder, intent]);

  const targetFolder = joinPath(folder, newFolder.trim());
  const name = filename.trim();
  const fullPath = joinPath(targetFolder, name);
  // The filename may itself carry subfolders ("ex03/notes.md"): it's just a path.
  const willUpdate = !isFolderIntent && existingPaths.has(fullPath);

  function onFile(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    if (!f) return;
    const reader = new FileReader();
    reader.onload = () => {
      const res = typeof reader.result === "string" ? reader.result : "";
      setB64(res.split(",")[1] ?? "");
      setFilename(f.name);
    };
    reader.readAsDataURL(f);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (isFolderIntent) {
      if (!newFolder.trim()) {
        setError(t("contribute.errFolder"));
        return;
      }
    } else {
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
    }
    const path = isFolderIntent ? targetFolder : fullPath;
    if (!validPath(path)) {
      setError(t("contribute.errPath"));
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const res = await api.contributeContent(
        isFolderIntent
          ? { section, path, create_folder: true, message: message.trim() || null }
          : {
              section,
              path,
              content: mode === "text" ? text : b64,
              encoding: mode === "text" ? "utf-8" : "base64",
              message: message.trim() || null,
            },
      );
      setResult(res);
      onDone?.();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("contribute.errGeneric"));
    } finally {
      setSubmitting(false);
    }
  }

  const chip = (active: boolean) =>
    cn(
      "border px-2.5 py-1 font-mono text-xs transition-colors rounded-[var(--radius-button)]",
      active
        ? "border-[var(--ring)] bg-[var(--surface-2)]"
        : "border-[var(--border)] bg-[var(--surface)] text-[var(--text-muted)] hover:text-[var(--text)]",
    );
  const label = "mb-1 block font-mono text-xs text-[var(--text-muted)]";
  const note = "mt-1 font-mono text-[11px] text-[var(--text-muted)]";

  const submitLabel = isFolderIntent
    ? t("contribute.submitFolder")
    : willUpdate
      ? t("contribute.submitUpdate")
      : t("contribute.submit");
  const submittingLabel = isFolderIntent
    ? t("contribute.submittingFolder")
    : willUpdate
      ? t("contribute.submittingUpdate")
      : t("contribute.submitting");
  const successBody = isFolderIntent
    ? t("contribute.successFolder")
    : result?.action === "updated"
      ? t("contribute.successUpdated")
      : t("contribute.successCreated");

  return (
    <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
      <DialogContent
        title={isFolderIntent ? t("contribute.titleFolder") : t("contribute.title")}
        barTitle={t("contribute.bar")}
      >
        {result ? (
          <div className="flex flex-col gap-3" role="status">
            <p className="font-display text-lg">{t("contribute.successTitle")}</p>
            <p className="font-mono text-sm text-[var(--text-muted)]">{successBody}</p>
            {isFolderIntent ? (
              <Button variant="outline" onClick={() => onOpenChange(false)}>
                {t("contribute.close")}
              </Button>
            ) : (
              <Button variant="outline" onClick={() => setResult(null)}>
                {t("contribute.another")}
              </Button>
            )}
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            {!isFolderIntent && (
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
            )}

            <div>
              <label className={label} htmlFor="contribute-folder">
                {t("contribute.folderLabel")}
              </label>
              <select
                id="contribute-folder"
                value={folder}
                onChange={(e) => setFolder(e.target.value)}
                className="w-full border border-[var(--border)] bg-[var(--surface)] px-2 py-2 font-mono text-sm rounded-[var(--radius-input)]"
              >
                <option value="">{t("contribute.folderRoot")}</option>
                {[...new Set([...folders, ...(initialFolder ? [initialFolder] : [])])]
                  .sort((a, b) => a.localeCompare(b))
                  .map((f) => (
                    <option key={f} value={f}>
                      {f}
                    </option>
                  ))}
              </select>
            </div>

            <div>
              <label className={label} htmlFor="contribute-newfolder">
                {isFolderIntent
                  ? t("contribute.newFolderRequiredLabel")
                  : t("contribute.newFolderLabel")}
              </label>
              <Input
                id="contribute-newfolder"
                value={newFolder}
                onChange={(e) => setNewFolder(e.target.value)}
                placeholder={t("contribute.newFolderPlaceholder")}
                maxLength={200}
              />
              <p className={note}>
                {isFolderIntent ? t("contribute.folderHelpEmpty") : t("contribute.folderHelp")}
              </p>
            </div>

            {!isFolderIntent &&
              (mode === "text" ? (
                <>
                  <div>
                    <label className={label}>{t("contribute.filenameLabel")}</label>
                    <Input
                      value={filename}
                      onChange={(e) => setFilename(e.target.value)}
                      placeholder={t("contribute.filenamePlaceholder")}
                      maxLength={120}
                    />
                  </div>
                  <div>
                    <label className={label}>{t("contribute.contentLabel")}</label>
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
                  <label className={label}>{t("contribute.fileLabel")}</label>
                  <label className="flex cursor-pointer items-center gap-2 border border-dashed border-[var(--border)] bg-[var(--surface)] px-3 py-3 font-mono text-xs hover:bg-[var(--surface-2)] rounded-[var(--radius-input)]">
                    <Upload className="h-4 w-4" />
                    <span className="truncate">{filename || t("contribute.fileLabel")}</span>
                    <input type="file" onChange={onFile} className="sr-only" />
                  </label>
                </div>
              ))}

            {willUpdate && (
              <p className="border border-[var(--border)] bg-[var(--surface-2)] px-2 py-1.5 font-mono text-xs rounded-[var(--radius-inner)]">
                {t("contribute.willOverwrite")} <span className="break-all">{fullPath}</span>
              </p>
            )}

            <div>
              <label className={label}>{t("contribute.messageLabel")}</label>
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
                {submitting ? submittingLabel : submitLabel}
              </Button>
            </div>
          </form>
        )}
      </DialogContent>
    </DialogPrimitive.Root>
  );
}
