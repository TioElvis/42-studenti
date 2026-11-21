"use client";

import * as React from "react";
import { FileText, Folder } from "lucide-react";

import { SectionHeading } from "@/components/chrome/section-heading";
import { Window, WindowBar } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { api, ApiError } from "@/lib/api";
import { useI18n } from "@/providers/i18n-provider";
import type { ContentEntry, ContentFile, ContentSection } from "@/lib/types";

/** Read-only file browser for the Materiale / Archivio content served from
 * assets/. Shows a folder-grouped file list; selecting a file renders its text
 * (as plain text — safe against XSS; Markdown shows as source). */
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
  const [selected, setSelected] = React.useState<string | null>(null);
  const [file, setFile] = React.useState<ContentFile | null>(null);
  const [fileError, setFileError] = React.useState<string | null>(null);
  const [loadingFile, setLoadingFile] = React.useState(false);

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

  const open = React.useCallback(
    (path: string) => {
      setSelected(path);
      setFile(null);
      setFileError(null);
      setLoadingFile(true);
      api
        .readContent(section, path)
        .then((f) => setFile(f))
        .catch((e) => setFileError(e instanceof ApiError ? e.message : t("content.error")))
        .finally(() => setLoadingFile(false));
    },
    [section, t],
  );

  const groups = React.useMemo(() => {
    const m = new Map<string, ContentEntry[]>();
    for (const e of entries ?? []) {
      const k = e.folder || "";
      const arr = m.get(k);
      if (arr) arr.push(e);
      else m.set(k, [e]);
    }
    return [...m.entries()].sort(([a], [b]) => a.localeCompare(b));
  }, [entries]);

  return (
    <section>
      <SectionHeading label={t(labelKey)} desc={t(descKey)} />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,320px)_1fr]">
        <Window className="retro-shadow self-start">
          <WindowBar title={bar} />
          <div className="p-3 font-mono text-sm">
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
                  {items.map((e) => (
                    <li key={e.path}>
                      <button
                        type="button"
                        onClick={() => open(e.path)}
                        disabled={!e.text}
                        aria-current={selected === e.path ? "true" : undefined}
                        className={cn(
                          "flex w-full items-center gap-2 border-l-2 px-2 py-1.5 text-left transition-colors",
                          selected === e.path
                            ? "border-[var(--primary)] bg-[var(--surface-2)]"
                            : "border-transparent hover:bg-[var(--surface-2)]",
                          !e.text && "cursor-not-allowed opacity-50",
                        )}
                      >
                        <FileText className="h-3.5 w-3.5 shrink-0 text-[var(--text-muted)]" aria-hidden />
                        <span className="truncate">{e.name}</span>
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </Window>

        <Window className="retro-shadow self-start">
          <WindowBar title={selected ?? "—"} />
          <div className="p-4">
            {!selected && (
              <p className="font-mono text-sm text-[var(--text-muted)]">{t("content.pick")}</p>
            )}
            {selected && loadingFile && <Skeleton className="h-40 w-full" />}
            {selected && fileError && (
              <p className="font-mono text-sm text-[var(--primary)]" role="alert">
                {fileError}
              </p>
            )}
            {file && !loadingFile && !fileError && (
              <pre className="overflow-x-auto whitespace-pre-wrap break-words font-mono text-sm leading-relaxed">
                {file.content}
              </pre>
            )}
          </div>
        </Window>
      </div>
    </section>
  );
}
