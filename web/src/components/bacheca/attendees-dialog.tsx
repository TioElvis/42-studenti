"use client";

import * as React from "react";
import Link from "next/link";
import * as DialogPrimitive from "@radix-ui/react-dialog";

import { DialogContent } from "@/components/ui/dialog";
import { Avatar } from "@/components/chrome/avatar";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { useI18n } from "@/providers/i18n-provider";
import type { UserPublic } from "@/lib/types";

/** CHI_CE_STA.EXE — the list of students who clicked "Ci sto!". */
export function AttendeesDialog({
  postId,
  onOpenChange,
}: {
  postId: number | null;
  onOpenChange: (open: boolean) => void;
}) {
  const { t } = useI18n();
  const [people, setPeople] = React.useState<UserPublic[] | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (postId == null) {
      setPeople(null);
      return;
    }
    let cancelled = false;
    setPeople(null);
    setError(null);
    api
      .listAttendees(postId)
      .then((list) => {
        if (!cancelled) setPeople(list);
      })
      .catch(() => {
        if (!cancelled) setError(t("attendees.error"));
      });
    return () => {
      cancelled = true;
    };
  }, [postId, t]);

  return (
    <DialogPrimitive.Root open={postId != null} onOpenChange={onOpenChange}>
      <DialogContent title={t("attendees.title")} barTitle={t("attendees.bar")}>
        {error && (
          <p className="font-mono text-sm text-[var(--primary)]" role="alert">
            {error}
          </p>
        )}
        {!error && people === null && (
          <div className="flex flex-col gap-2">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
          </div>
        )}
        {people && people.length === 0 && (
          <p className="border border-dashed border-[var(--border)] p-3 text-center font-mono text-xs text-[var(--text-muted)]">
            {t("attendees.empty")}
          </p>
        )}
        {people && people.length > 0 && (
          <ul className="flex flex-col gap-2">
            {people.map((p) => (
              <li key={p.id}>
                <Link
                  href={`/u/${p.login}`}
                  className="flex items-center gap-2.5 border border-[var(--border-subtle)] bg-[var(--surface-sunken)] p-2 transition-colors hover:bg-[var(--surface-2)]"
                >
                  <Avatar user={p} size={28} />
                  <span className="min-w-0">
                    <span className="block truncate font-mono text-sm font-bold">@{p.login}</span>
                    {p.display_name && (
                      <span className="block truncate text-xs text-[var(--text-muted)]">
                        {p.display_name}
                      </span>
                    )}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </DialogContent>
    </DialogPrimitive.Root>
  );
}
