import * as React from "react";
import { cn } from "@/lib/utils";

const base =
  "w-full bg-[var(--surface-sunken)] text-[var(--text)] border border-[var(--border)] px-3 py-2 text-sm font-mono placeholder:text-[var(--text-muted)] focus-visible:outline-2 focus-visible:outline-offset-2";

export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...props }, ref) => (
    <input ref={ref} className={cn(base, className)} {...props} />
  ),
);
Input.displayName = "Input";

export const Textarea = React.forwardRef<
  HTMLTextAreaElement,
  React.TextareaHTMLAttributes<HTMLTextAreaElement>
>(({ className, ...props }, ref) => (
  <textarea ref={ref} className={cn(base, "resize-y min-h-24", className)} {...props} />
));
Textarea.displayName = "Textarea";
