"use client";

import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 border font-mono text-sm font-medium cursor-pointer select-none transition-colors disabled:opacity-50 disabled:pointer-events-none focus-visible:outline-2 focus-visible:outline-offset-2",
  {
    variants: {
      variant: {
        primary:
          "bg-[var(--primary)] text-[var(--primary-fg)] border-[var(--border)] retro-shadow-sm hover:bg-[var(--primary-hover)] active:translate-x-px active:translate-y-px",
        outline:
          "bg-[var(--surface)] text-[var(--text)] border-[var(--border)] retro-shadow-sm hover:bg-[var(--surface-2)] active:translate-x-px active:translate-y-px",
        ghost:
          "bg-transparent text-[var(--text)] border-transparent hover:bg-[var(--surface-2)]",
        danger:
          "bg-transparent text-[var(--primary)] border-[var(--primary)] hover:bg-[var(--primary)] hover:text-[var(--primary-fg)]",
      },
      size: {
        sm: "h-8 px-3 text-xs",
        md: "h-10 px-4",
        lg: "h-11 px-6",
        icon: "h-9 w-9 p-0",
      },
    },
    defaultVariants: { variant: "primary", size: "md" },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp ref={ref} className={cn(buttonVariants({ variant, size }), className)} {...props} />
    );
  },
);
Button.displayName = "Button";

export { buttonVariants };
