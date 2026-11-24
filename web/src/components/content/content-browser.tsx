"use client";

import * as React from "react";
import {
  Download,
  ExternalLink,
  File,
  FileText,
  Folder,
  Image as ImageIcon,
  Search,
} from "lucide-react";

import { SectionHeading } from "@/components/chrome/section-heading";
import { Button } from "@/components/ui/button";
import { Window, WindowBar } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { ContributeModal } from "./contribute-modal";
import { cn } from "@/lib/utils";
import { api, ApiError } from "@/lib/api";
import { useI18n } from "@/providers/i18n-provider";
import type {
  ContentEntry,
  ContentFile,
  ContentKind,
  ContentSection,
  GithubStatus,
} from "@/lib/types";

const ICON: Record<ContentKind, typeof File> = {
  text: FileText,
  image: ImageIcon,
  pdf: FileText,
  other: File,
};

/** Read-only file browser for Materiale / Archivio (served from assets/).
 * Text renders as plain text (XSS-safe), images and PDFs render inline, and
 * every file can be downloaded or opened in a new tab. */
export function ContentBrowser({
  section,
  labelKey,
  descKey,
  bar,
}: {
  section: ContentSection;
  labelKey: string;
  descKey: string;
  bar: string;
}) {
  const { t } = useI18n();
  const [entries, setEntries] = React.useState<ContentEntry[] | null>(null);
  const [listError, setListError] = React.useState<string | null>(null);
  const [selected, setSelected] = React.useState<ContentEntry | null>(null);
  const [file, setFile] = React.useState<ContentFile | null>(null);
  const [fileError, setFileError] = React.useState<string | null>(null);
  const [loadingFile, setLoadingFile] = React.useState(false);
  const [query, setQuery] = React.useState("");
  const [gh, setGh] = React.useState<GithubStatus | null>(null);
  const [contributeOpen, setContributeOpen] = React.useState(false);

  React.useEffect(() => {
    let cancelled = false;
    api
      .listContent(section)
      .then((r) => {
        if (!cancelled) setEntries(r.entries);
      })
      .catch((e) => {
        if (!cancelled) setListError(e instanceof ApiError ? e.message : t("content.listError"));
      });
    return () => {
      cancelled = true;
    };
  }, [section, t]);

  // GitHub contribution availability (feature hidden unless configured).
  React.useEffect(() => {
    let cancelled = false;
    api
      .githubStatus()
      .then((s) => {
        if (!cancelled) setGh(s);
      })
      .catch(() => {
        /* status is optional UI sugar — ignore errors */
      });
    return () => {
      cancelled = true;
    };
  }, []);


  const open = React.useCallback(
    (entry: ContentEntry) => {
      setSelected(entry);
      setFile(null);
      setFileError(null);
      if (entry.kind !== "text") return; // non-text renders from its URL directly
      setLoadingFile(true);
      api
        .readContent(section, entry.path)
        .then((f) => setFile(f))
        .catch((e) => setFileError(e instanceof ApiError ? e.message : t("content.error")))
        .finally(() => setLoadingFile(false));
    },
    [section, t],
  );

  const groups = React.useMemo(() => {
    const q = query.trim().toLowerCase();
    const m = new Map<string, ContentEntry[]>();
    for (const e of entries ?? []) {
      if (
        q &&
        !e.name.toLowerCase().includes(q) &&
        !e.folder.toLowerCase().includes(q) &&
        !e.path.toLowerCase().includes(q)
      ) {
        continue;
      }
      const k = e.folder || "";
      const arr = m.get(k);
      if (arr) arr.push(e);
      else m.set(k, [e]);
    }
    return [...m.entries()].sort(([a], [b]) => a.localeCompare(b));
  }, [entries, query]);

  return (
    <section>
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <SectionHeading label={t(labelKey)} desc={t(descKey)} />
        {gh?.configured &&
          (gh.server_mode || gh.linked) &&
          (section === "material" || gh.can_archive) && (
            <Button size="sm" onClick={() => setContributeOpen(true)}>
              {t("content.contribute")}
            </Button>
          )}
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,320px)_1fr]">
        {/* File list */}
        <Window className="retro-shadow self-start">
          <WindowBar title={bar} />
          <div className="p-3 font-mono text-sm">
            {entries && entries.length > 0 && (
              <div className="relative mb-3">
                <Search
                  className="pointer-events-none absolute left-2 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[var(--text-muted)]"
                  aria-hidden
                />
                <Input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder={t("content.search")}
                  aria-label={t("content.search")}
                  className="pl-7"
                />
              </div>
            )}
            {entries === null && !listError && (
              <>
                <Skeleton className="mb-2 h-8 w-full" />
                <Skeleton className="h-8 w-full" />
              </>
            )}
            {listError && <p className="text-[var(--primary)]">{listError}</p>}
            {entries && entries.length === 0 && (
              <p className="text-xs text-[var(--text-muted)]">{t("content.empty")}</p>
            )}
            {groups.map(([folder, items]) => (
              <div key={folder || "__root"} className="mb-3 last:mb-0">
                <div className="mb-1 flex items-center gap-1.5 text-[11px] text-[var(--text-muted)]">
                  <Folder className="h-3 w-3" aria-hidden /> {folder || t("content.root")}
                </div>
                <ul className="flex flex-col">
                  {items.map((e) => {
                    const Icon = ICON[e.kind];
                    return (
                      <li key={e.path}>
                        <button
                          type="button"
                          onClick={() => open(e)}
                          aria-current={selected?.path === e.path ? "true" : undefined}
                          className={cn(
                            "flex w-full items-center gap-2 border-l-2 px-2 py-1.5 text-left transition-colors",
                            selected?.path === e.path
                              ? "border-[var(--primary)] bg-[var(--surface-2)]"
                              : "border-transparent hover:bg-[var(--surface-2)]",
                          )}
                        >
                          <Icon className="h-3.5 w-3.5 shrink-0 text-[var(--text-muted)]" aria-hidden />
                          <span className="truncate">{e.name}</span>
                        </button>
                      </li>
                    );
                  })}
                </ul>
              </div>
            ))}
            {entries && entries.length > 0 && groups.length === 0 && (
              <p className="text-xs text-[var(--text-muted)]">{t("content.noMatch")}</p>
            )}
          </div>
        </Window>

        {/* Viewer */}
        <Window className="retro-shadow self-start">
          <WindowBar title={selected?.path ?? "—"} />
          <div className="p-4">
            {!selected && (
              <p className="font-mono text-sm text-[var(--text-muted)]">{t("content.pick")}</p>
            )}

            {selected && (
              <div className="flex flex-col gap-3">
                <div className="flex flex-wrap gap-2">
                  <Button asChild size="sm">
                    <a href={api.contentFileUrl(section, selected.path, true)}>
                      <Download className="h-4 w-4" /> {t("content.download")}
                    </a>
                  </Button>
                  {selected.kind !== "text" && (
                    <Button asChild size="sm" variant="outline">
                      <a
                        href={api.contentFileUrl(section, selected.path)}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        <ExternalLink className="h-4 w-4" /> {t("content.openTab")}
                      </a>
                    </Button>
                  )}
                </div>

                {selected.kind === "text" &&
                  (loadingFile ? (
                    <Skeleton className="h-40 w-full" />
                  ) : fileError ? (
                    <p className="font-mono text-sm text-[var(--primary)]" role="alert">
                      {fileError}
                    </p>
                  ) : file ? (
                    <pre className="overflow-x-auto whitespace-pre-wrap break-words border border-[var(--border-subtle)] bg-[var(--surface-sunken)] p-3 font-mono text-sm leading-relaxed">
                      {file.content}
                    </pre>
                  ) : null)}

                {selected.kind === "image" && (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={api.contentFileUrl(section, selected.path)}
                    alt={selected.name}
                    className="max-w-full border border-[var(--border)] bg-[var(--surface-2)]"
                  />
                )}

                {selected.kind === "pdf" && (
                  <iframe
                    src={api.contentFileUrl(section, selected.path)}
                    title={selected.name}
                    className="h-[70vh] w-full border border-[var(--border)] bg-[var(--surface-2)]"
                  />
                )}

                {selected.kind === "other" && (
                  <p className="border border-dashed border-[var(--border)] p-4 text-center font-mono text-sm text-[var(--text-muted)]">
                    {t("content.noPreview")}
                  </p>
                )}
              </div>
            )}
          </div>
        </Window>
      </div>

      <ContributeModal open={contributeOpen} onOpenChange={setContributeOpen} section={section} />
    </section>
  );
}
