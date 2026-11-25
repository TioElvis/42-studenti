"use client";

import * as React from "react";
import * as DialogPrimitive from "@radix-ui/react-dialog";

import { DialogContent } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { api, ApiError } from "@/lib/api";
import { useI18n } from "@/providers/i18n-provider";
import type { ContentSection } from "@/lib/types";

/** Confirm, then delete a file or a whole folder from assets/<section>/.
 * The server re-checks that the caller is a special user. */
export function DeleteConfirm({
  target,
  section,
  onClose,
  onDeleted,
}: {
  /** What to delete; `null` keeps the dialog closed. */
  target: { path: string; folder: boolean } | null;
  section: ContentSection;
  onClose: () => void;
  onDeleted: () => void;
}) {
  const { t } = useI18n();
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    setError(null);
    setBusy(false);
  }, [target]);

  async function confirm() {
    if (!target) return;
    setBusy(true);
    setError(null);
    try {
      await api.deleteContent({ section, path: target.path, folder: target.folder });
      onDeleted();
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("delete.errGeneric"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <DialogPrimitive.Root open={target !== null} onOpenChange={(o) => !o && !busy && onClose()}>
      <DialogContent
        title={target?.folder ? t("delete.titleFolder") : t("delete.titleFile")}
        barTitle={t("delete.bar")}
      >
        <div className="flex flex-col gap-4">
          <p className="font-mono text-sm">
            {target?.folder ? t("delete.confirmFolder") : t("delete.confirmFile")}
          </p>
          <p className="break-all border border-[var(--border)] bg-[var(--surface-2)] px-2 py-1.5 font-mono text-xs rounded-[var(--radius-inner)]">
            {target?.path}
          </p>
          <p className="font-mono text-[11px] text-[var(--text-muted)]">
            {target?.folder ? t("delete.noteFolder") : t("delete.noteFile")}
          </p>
          {error && (
            <p className="font-mono text-xs text-[var(--primary)]" role="alert">
              {error}
            </p>
          )}
          <div className="flex justify-end gap-2">
            <Button type="button" variant="ghost" onClick={onClose} disabled={busy}>
              {t("common.cancel")}
            </Button>
            <Button type="button" variant="danger" onClick={() => void confirm()} disabled={busy}>
              {busy ? t("delete.deleting") : t("common.delete")}
            </Button>
          </div>
        </div>
      </DialogContent>
    </DialogPrimitive.Root>
  );
}
