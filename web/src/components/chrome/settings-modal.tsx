"use client";

import * as React from "react";
import { Settings2, Check } from "lucide-react";

import { Dialog, DialogContent, DialogTrigger } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useTheme, type Theme } from "@/providers/theme-provider";
import { useI18n } from "@/providers/i18n-provider";
import { LANGS } from "@/lib/messages";
import { NotificationSettingsSection } from "@/components/notifications/notification-settings";

interface ThemeOption {
  id: Theme;
  name: string;
  subKey: string;
  swatches: string[];
}

const OPTIONS: ThemeOption[] = [
  {
    id: "classic",
    name: "Classico Romano",
    subKey: "settings.classicSub",
    swatches: ["#f6f2e9", "#9b2928", "#dce8d0", "#f7e6b0", "#2b2927"],
  },
  {
    id: "hacker",
    name: "SPQR Hacker",
    subKey: "settings.hackerSub",
    swatches: ["#0b0d0e", "#00ff88", "#e63946", "#00e5ff", "#ffb703"],
  },
];

export function SettingsModal({ compact = false }: { compact?: boolean }) {
  const { theme, setTheme } = useTheme();
  const { lang, setLang, t } = useI18n();
  const [open, setOpen] = React.useState(false);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" size={compact ? "icon" : "sm"} aria-label={t("settings.trigger")}>
          <Settings2 className="h-4 w-4" />
          {!compact && <span>{t("settings.trigger")}</span>}
        </Button>
      </DialogTrigger>
      <DialogContent title={t("settings.title")} barTitle={t("settings.bar")}>
        {/* Theme */}
        <h3 className="mb-1 font-mono text-xs font-bold uppercase tracking-wide text-[var(--text-muted)]">
          {t("settings.themeHeading")}
        </h3>
        <p className="mb-3 text-sm text-[var(--text-muted)]">{t("settings.themeIntro")}</p>
        <div className="flex flex-col gap-3">
          {OPTIONS.map((opt) => {
            const active = theme === opt.id;
            return (
              <button
                key={opt.id}
                type="button"
                onClick={() => setTheme(opt.id)}
                aria-pressed={active}
                className={cn(
                  "flex items-center gap-3 border p-3 text-left transition-colors hover-lift",
                  active
                    ? "border-[var(--ring)] bg-[var(--surface-2)]"
                    : "border-[var(--border)] bg-[var(--surface)]",
                )}
              >
                <span className="flex shrink-0">
                  {opt.swatches.map((c, i) => (
                    <span
                      key={i}
                      className="h-6 w-5 border border-[var(--border)]"
                      style={{ background: c, marginLeft: i === 0 ? 0 : -1 }}
                    />
                  ))}
                </span>
                <span className="flex-1">
                  <span className="block font-mono text-sm font-bold">{opt.name}</span>
                  <span className="block text-xs text-[var(--text-muted)]">{t(opt.subKey)}</span>
                </span>
                {active && <Check className="h-4 w-4 text-[var(--ring)]" aria-hidden />}
              </button>
            );
          })}
        </div>

        {/* Language */}
        <h3 className="mb-1 mt-5 font-mono text-xs font-bold uppercase tracking-wide text-[var(--text-muted)]">
          {t("settings.langHeading")}
        </h3>
        <p className="mb-3 text-sm text-[var(--text-muted)]">{t("settings.langIntro")}</p>
        <div className="flex gap-2">
          {LANGS.map((l) => {
            const active = lang === l.id;
            return (
              <button
                key={l.id}
                type="button"
                onClick={() => setLang(l.id)}
                aria-pressed={active}
                className={cn(
                  "flex flex-1 items-center justify-center gap-2 border px-3 py-2 font-mono text-sm transition-colors",
                  active
                    ? "border-[var(--ring)] bg-[var(--surface-2)] font-bold"
                    : "border-[var(--border)] bg-[var(--surface)] text-[var(--text-muted)] hover:text-[var(--text)]",
                )}
              >
                {active && <Check className="h-4 w-4 text-[var(--ring)]" aria-hidden />}
                {l.label}
              </button>
            );
          })}
        </div>

        {/* Notifications */}
        <h3 className="mb-1 mt-5 font-mono text-xs font-bold uppercase tracking-wide text-[var(--text-muted)]">
          {t("notifications.settingsHeading")}
        </h3>
        <p className="mb-3 text-sm text-[var(--text-muted)]">
          {t("notifications.settingsIntro")}
        </p>
        {open && <NotificationSettingsSection />}
      </DialogContent>
    </Dialog>
  );
}
