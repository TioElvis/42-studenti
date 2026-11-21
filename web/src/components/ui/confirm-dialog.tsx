"use client";

import * as React from "react";
import * as DialogPrimitive from "@radix-ui/react-dialog";

import { DialogContent } from "./dialog";
import { Button } from "./button";
import { useI18n } from "@/providers/i18n-provider";

/** A styled confirmation dialog (replaces window.confirm for destructive actions). */
export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmLabel,
  cancelLabel,
  onConfirm,
  barTitle,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: React.ReactNode;
  confirmLabel?: string;
  cancelLabel?: string;
  onConfirm: () => void | Promise<void>;
  barTitle?: string;
}) {
  const { t } = useI18n();
  const [busy, setBusy] = React.useState(false);

  async function handleConfirm() {
    setBusy(true);
    try {
      await onConfirm();
      onOpenChange(false);
    } finally {
      setBusy(false);
    }
  }

  return (
    <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
      <DialogContent title={title} barTitle={barTitle ?? t("common.confirmBar")}>
        <div className="mb-5 text-sm text-[var(--text-muted)]">{description}</div>
        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={() => onOpenChange(false)} disabled={busy}>
            {cancelLabel ?? t("common.cancel")}
          </Button>
          <Button variant="primary" onClick={handleConfirm} disabled={busy}>
            {busy ? t("common.wait") : confirmLabel ?? t("common.confirm")}
          </Button>
        </div>
      </DialogContent>
    </DialogPrimitive.Root>
  );
}
