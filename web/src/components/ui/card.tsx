import * as React from "react";
import { cn } from "@/lib/utils";

/** A retro OS "window" surface with a title bar and window dots. */
export function Window({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("window", className)} {...props} />;
}

export function WindowBar({
  title,
  className,
  children,
  dots = 3,
}: {
  title?: React.ReactNode;
  className?: string;
  children?: React.ReactNode;
  dots?: number;
}) {
  return (
    <div className={cn("window-bar", className)}>
      <span className="truncate">{title ?? children}</span>
      <span className="window-dots" aria-hidden>
        {Array.from({ length: dots }).map((_, i) => (
          <span key={i} />
        ))}
      </span>
    </div>
  );
}

export function Card({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "bg-[var(--surface)] border border-[var(--border)] p-4 rounded-[var(--radius-card)]",
        className,
      )}
      {...props}
    />
  );
}
