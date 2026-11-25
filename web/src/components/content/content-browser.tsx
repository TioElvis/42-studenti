"use client";

import * as React from "react";
import {
  ChevronDown,
  ChevronRight,
  Download,
  ExternalLink,
  File,
  FileText,
  Folder,
  FolderPlus,
  Image as ImageIcon,
  Search,
  Upload,
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

interface TreeNode {
  name: string;
  path: string;
  folders: TreeNode[];
  files: ContentEntry[];
}

/** Build a nested folder tree from the flat listing. `.gitkeep`-only folders
 * come from `folders` and have no files, so they never inflate file counts. */
function buildTree(folders: string[], entries: ContentEntry[]): TreeNode {
  const root: TreeNode = { name: "", path: "", folders: [], files: [] };
  const index = new Map<string, TreeNode>([["", root]]);
  const ensure = (path: string): TreeNode => {
    const hit = index.get(path);
    if (hit) return hit;
    const cut = path.lastIndexOf("/");
    const parent = ensure(cut === -1 ? "" : path.slice(0, cut));
    const node: TreeNode = { name: path.slice(cut + 1), path, folders: [], files: [] };
    parent.folders.push(node);
    index.set(path, node);
    return node;
  };
  for (const f of folders) if (f) ensure(f);
  for (const e of entries) ensure(e.folder).files.push(e);
  const sort = (n: TreeNode) => {
    n.folders.sort((a, b) => a.name.localeCompare(b.name));
    n.files.sort((a, b) => a.name.localeCompare(b.name));
    n.folders.forEach(sort);
  };
  sort(root);
  return root;
}

function countFiles(n: TreeNode): number {
  return n.files.length + n.folders.reduce((acc, f) => acc + countFiles(f), 0);
}

/** File browser for Materiale / Archivio (listed from GitHub's assets/).
 * Text renders as plain text (XSS-safe), images and PDFs render inline, and
 * every file can be downloaded or opened in a new tab. Folders (any depth) get
 * contextual "upload here" / "new subfolder" actions when contributing is on. */
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
  const [folders, setFolders] = React.useState<string[]>([]);
  const [collapsed, setCollapsed] = React.useState<ReadonlySet<string>>(new Set());
  const [listError, setListError] = React.useState<string | null>(null);
  const [selected, setSelected] = React.useState<ContentEntry | null>(null);
  const [file, setFile] = React.useState<ContentFile | null>(null);
  const [fileError, setFileError] = React.useState<string | null>(null);
  const [loadingFile, setLoadingFile] = React.useState(false);
  const [query, setQuery] = React.useState("");
  const [gh, setGh] = React.useState<GithubStatus | null>(null);
  const [contribute, setContribute] = React.useState<{
    open: boolean;
    intent: "upload" | "folder";
    folder: string;
  }>({ open: false, intent: "upload", folder: "" });

  const load = React.useCallback(() => {
    return api
      .listContent(section)
      .then((r) => {
        setEntries(r.entries);
        setFolders(r.folders ?? []);
        setListError(null);
      })
      .catch((e) => {
        setListError(e instanceof ApiError ? e.message : t("content.listError"));
      });
  }, [section, t]);

  React.useEffect(() => {
    void load();
  }, [load]);

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

  const query_ = query.trim().toLowerCase();
  const tree = React.useMemo(() => {
    const q = query_;
    const list = (entries ?? []).filter(
      (e) =>
        !q ||
        e.name.toLowerCase().includes(q) ||
        e.folder.toLowerCase().includes(q) ||
        e.path.toLowerCase().includes(q),
    );
    // While searching, show only folders that lead to a match (no empty ones).
    return buildTree(q ? [] : folders, list);
  }, [entries, folders, query_]);
  const existingPaths = React.useMemo(
    () => new Set((entries ?? []).map((e) => e.path)),
    [entries],
  );
  const canContribute =
    !!gh?.configured &&
    (gh.server_mode || gh.linked) &&
    (section === "material" || !!gh.can_archive);
  const hasAny = tree.files.length > 0 || tree.folders.length > 0;

  const toggle = (path: string) =>
    setCollapsed((prev) => {
      const next = new Set(prev);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });

  const iconBtn =
    "inline-flex h-5 w-5 shrink-0 items-center justify-center text-[var(--text-muted)] transition-colors hover:text-[var(--text)] rounded-[var(--radius-inner)]";

  const renderFolderActions = (path: string, label: string) =>
    canContribute && (
      <span className="ml-auto flex shrink-0 items-center gap-0.5">
        <button
          type="button"
          className={iconBtn}
          title={t("content.uploadIn", { name: label })}
          aria-label={t("content.uploadIn", { name: label })}
          onClick={() => setContribute({ open: true, intent: "upload", folder: path })}
        >
          <Upload className="h-3 w-3" aria-hidden />
        </button>
        <button
          type="button"
          className={iconBtn}
          title={t("content.newFolderIn", { name: label })}
          aria-label={t("content.newFolderIn", { name: label })}
          onClick={() => setContribute({ open: true, intent: "folder", folder: path })}
        >
          <FolderPlus className="h-3 w-3" aria-hidden />
        </button>
      </span>
    );

  const renderFile = (e: ContentEntry) => {
    const Icon = ICON[e.kind];
    return (
      <li key={e.path}>
        <button
          type="button"
          onClick={() => open(e)}
          aria-current={selected?.path === e.path ? "true" : undefined}
          className={cn(
            "flex w-full items-center gap-2 border-l-2 px-2 py-1.5 text-left transition-colors rounded-[var(--radius-inner)]",
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
  };

  const renderNode = (node: TreeNode): React.ReactNode => {
    // Searching expands everything so matches are never hidden.
    const isCollapsed = !query_ && collapsed.has(node.path);
    return (
      <li key={node.path}>
        <div className="flex items-center gap-1 text-[11px] text-[var(--text-muted)]">
          <button
            type="button"
            onClick={() => toggle(node.path)}
            aria-expanded={!isCollapsed}
            className="flex min-w-0 items-center gap-1.5 py-1 hover:text-[var(--text)]"
          >
            {isCollapsed ? (
              <ChevronRight className="h-3 w-3 shrink-0" aria-hidden />
            ) : (
              <ChevronDown className="h-3 w-3 shrink-0" aria-hidden />
            )}
            <Folder className="h-3 w-3 shrink-0" aria-hidden />
            <span className="truncate">{node.name}</span>
            <span className="shrink-0 opacity-70">({countFiles(node)})</span>
          </button>
          {renderFolderActions(node.path, node.path)}
        </div>
        {!isCollapsed && (
          <ul className="ml-2 flex flex-col border-l border-[var(--border-subtle)] pl-2">
            {node.folders.map(renderNode)}
            {node.files.map(renderFile)}
          </ul>
        )}
      </li>
    );
  };

  return (
    <section>
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <SectionHeading label={t(labelKey)} desc={t(descKey)} />
        {canContribute && (
          <Button
            size="sm"
            onClick={() => setContribute({ open: true, intent: "upload", folder: "" })}
          >
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
            {entries && !hasAny && !query_ && (
              <p className="text-xs text-[var(--text-muted)]">{t("content.empty")}</p>
            )}
            {entries && (hasAny || canContribute) && (
              <div className="mb-1 flex items-center gap-1 text-[11px] text-[var(--text-muted)]">
                <Folder className="h-3 w-3" aria-hidden /> {t("content.root")}
                {renderFolderActions("", t("content.root"))}
              </div>
            )}
            {hasAny && (
              <ul className="flex flex-col">
                {tree.folders.map(renderNode)}
                {tree.files.map(renderFile)}
              </ul>
            )}
            {entries && entries.length > 0 && !hasAny && query_ && (
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
                  {selected.github_url && (
                    <Button asChild size="sm" variant="outline">
                      <a href={selected.github_url} target="_blank" rel="noopener noreferrer">
                        <ExternalLink className="h-4 w-4" /> {t("content.openGithub")}
                      </a>
                    </Button>
                  )}
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
                    <pre className="overflow-x-auto whitespace-pre-wrap break-words border border-[var(--border-subtle)] bg-[var(--surface-sunken)] p-3 font-mono text-sm leading-relaxed rounded-[var(--radius-inner)]">
                      {file.content}
                    </pre>
                  ) : null)}

                {selected.kind === "image" && (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={api.contentFileUrl(section, selected.path)}
                    alt={selected.name}
                    className="max-w-full border border-[var(--border)] bg-[var(--surface-2)] rounded-[var(--radius-inner)]"
                  />
                )}

                {selected.kind === "pdf" && (
                  <iframe
                    src={api.contentFileUrl(section, selected.path)}
                    title={selected.name}
                    className="h-[70vh] w-full border border-[var(--border)] bg-[var(--surface-2)] rounded-[var(--radius-inner)]"
                  />
                )}

                {selected.kind === "other" && (
                  <p className="border border-dashed border-[var(--border)] p-4 text-center font-mono text-sm text-[var(--text-muted)] rounded-[var(--radius-inner)]">
                    {t("content.noPreview")}
                  </p>
                )}
              </div>
            )}
          </div>
        </Window>
      </div>

      <ContributeModal
        open={contribute.open}
        onOpenChange={(o) => setContribute((c) => ({ ...c, open: o }))}
        section={section}
        intent={contribute.intent}
        initialFolder={contribute.folder}
        folders={folders}
        existingPaths={existingPaths}
        onDone={() => void load()}
      />
    </section>
  );
}
