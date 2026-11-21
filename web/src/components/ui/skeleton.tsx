import { cn } from "@/lib/utils";

export function Skeleton({ className }: { className?: string }) {
  return (
    <div
      className={cn("animate-pulse bg-[var(--surface-2)] border border-[var(--border-subtle)]", className)}
      aria-hidden
    />
  );
}
