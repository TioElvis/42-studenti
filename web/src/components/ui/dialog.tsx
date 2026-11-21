"use client";

import * as React from "react";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import { X } from "lucide-react";

import { cn } from "@/lib/utils";

export const Dialog = DialogPrimitive.Root;
export const DialogTrigger = DialogPrimitive.Trigger;
export const DialogClose = DialogPrimitive.Close;

export function DialogContent({
  className,
  children,
  title,
  barTitle,
}: {
  className?: string;
  children: React.ReactNode;
  /** Visible heading inside the modal body. */
  title: string;
  /** Monospace label shown in the retro window bar, e.g. NUOVO_MESSAGGIO.EXE */
  barTitle: string;
}) {
  return (
    <DialogPrimitive.Portal>
      <DialogPrimitive.Overlay className="fixed inset-0 z-[70] bg-black/55 backdrop-blur-[1px]" />
      <DialogPrimitive.Content
        className={cn(
          "fixed left-1/2 top-1/2 z-[80] w-[calc(100vw-2rem)] max-w-lg -translate-x-1/2 -translate-y-1/2",
          "window retro-shadow-lg focus:outline-none",
          "max-h-[90vh] overflow-hidden flex flex-col",
          className,
        )}
      >
        <div className="window-bar shrink-0">
          <span className="truncate">{barTitle}</span>
          <DialogPrimitive.Close
            aria-label="Chiudi"
            className="cursor-pointer hover:text-[var(--primary)] transition-colors"
          >
            <X className="h-4 w-4" />
          </DialogPrimitive.Close>
        </div>
        <div className="overflow-y-auto overflow-x-hidden p-5">
          <DialogPrimitive.Title className="font-display text-lg mb-4">
            {title}
          </DialogPrimitive.Title>
          {children}
        </div>
      </DialogPrimitive.Content>
    </DialogPrimitive.Portal>
  );
}
