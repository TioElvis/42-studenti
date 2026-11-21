"use client";

import { Lock, Send, Lightbulb, Bug, HelpCircle } from "lucide-react";

import { SectionHeading } from "@/components/chrome/section-heading";
import { Window, WindowBar } from "@/components/ui/card";
import { useI18n } from "@/providers/i18n-provider";

export function StaffComingSoon() {
  const { t } = useI18n();

  const categories = [
    { icon: Lightbulb, label: t("staff.catSuggestion") },
    { icon: Bug, label: t("staff.catProblem") },
    { icon: HelpCircle, label: t("staff.catQuestion") },
  ];

  return (
    <section>
      <SectionHeading label={t("staff.label")} desc={t("staff.desc")} />

      <Window className="retro-shadow-lg relative overflow-hidden">
        <WindowBar title={t("staff.bar")}>
          <span className="inline-flex items-center gap-1.5">
            <span
              className="h-2 w-2 rounded-full"
              style={{ background: "var(--cat-evento_casuale-fg)" }}
              aria-hidden
            />
            {t("staff.channel")}
          </span>
        </WindowBar>

        {/* Preview of the future composer — inert, shown behind a lock overlay. */}
        <div className="pointer-events-none select-none p-5" aria-hidden>
          <div className="mb-2 font-mono text-[11px] text-[var(--text-muted)]">
            root@42roma:~$ ./new_message --to=staff
          </div>

          <div className="mb-4 flex flex-wrap gap-2">
            {categories.map(({ icon: Icon, label }, i) => (
              <span
                key={label}
                className={
                  "inline-flex items-center gap-1.5 border px-2.5 py-1 font-mono text-xs " +
                  (i === 0
                    ? "border-[var(--ring)] bg-[var(--surface-2)]"
                    : "border-[var(--border)] bg-[var(--surface)] text-[var(--text-muted)]")
                }
              >
                <Icon className="h-3.5 w-3.5" /> {label}
              </span>
            ))}
          </div>

          <div className="min-h-28 border border-[var(--border)] bg-[var(--surface-sunken)] p-3 font-mono text-sm text-[var(--text-muted)]">
            {t("staff.composerPlaceholder")}
            <span className="cursor-blink">_</span>
          </div>

          <div className="mt-3 flex items-center justify-end gap-2">
            <span className="font-mono text-[11px] text-[var(--text-muted)]">
              {t("staff.directTo")}
            </span>
            <span className="inline-flex items-center gap-2 border border-[var(--border)] bg-[var(--primary)] px-4 py-2 font-mono text-sm text-[var(--primary-fg)] retro-shadow-sm opacity-70">
              <Send className="h-4 w-4" /> {t("staff.sendBtn")}
            </span>
          </div>
        </div>

        {/* Lock overlay that marks the whole composer as not-yet-available. */}
        <div
          className="absolute inset-0 flex flex-col items-center justify-center gap-3 text-center"
          style={{ background: "color-mix(in srgb, var(--surface) 72%, transparent)" }}
        >
          <div className="flex h-12 w-12 items-center justify-center border border-[var(--border)] bg-[var(--surface-2)] retro-shadow-sm">
            <Lock className="h-6 w-6" />
          </div>
          <h3 className="font-display text-xl font-bold">
            {t("staff.lockTitle")}
            <span className="cursor-blink">_</span>
          </h3>
          <p className="max-w-sm px-4 font-mono text-xs text-[var(--text-muted)]">
            {t("staff.lockBody")}
          </p>
        </div>
      </Window>
    </section>
  );
}
