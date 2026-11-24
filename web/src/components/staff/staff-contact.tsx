"use client";

import * as React from "react";
import { Send, Lightbulb, Bug, HelpCircle } from "lucide-react";

import { SectionHeading } from "@/components/chrome/section-heading";
import { Window, WindowBar } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input, Textarea } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { useI18n } from "@/providers/i18n-provider";

// Configurable per deployment; falls back to a sensible placeholder.
const STAFF_EMAIL = process.env.NEXT_PUBLIC_STAFF_EMAIL || "staff@42roma.it";

type Provider = "gmail" | "outlook" | "default";
type Category = "suggestion" | "problem" | "question";

/** Build a pre-filled compose URL for the chosen email client. */
function composeUrl(provider: Provider, to: string, subject: string, body: string): string {
  const su = encodeURIComponent(subject);
  const bo = encodeURIComponent(body);
  if (provider === "gmail") {
    return `https://mail.google.com/mail/?view=cm&fs=1&to=${encodeURIComponent(to)}&su=${su}&body=${bo}`;
  }
  if (provider === "outlook") {
    return `https://outlook.office.com/mail/deeplink/compose?to=${encodeURIComponent(to)}&subject=${su}&body=${bo}`;
  }
  return `mailto:${to}?subject=${su}&body=${bo}`;
}

export function StaffContact() {
  const { t } = useI18n();
  const [category, setCategory] = React.useState<Category>("suggestion");
  const [subject, setSubject] = React.useState("");
  const [message, setMessage] = React.useState("");
  const [provider, setProvider] = React.useState<Provider>("gmail");
  const [error, setError] = React.useState<string | null>(null);

  const CATS: { id: Category; icon: typeof Lightbulb; label: string }[] = [
    { id: "suggestion", icon: Lightbulb, label: t("staff.catSuggestion") },
    { id: "problem", icon: Bug, label: t("staff.catProblem") },
    { id: "question", icon: HelpCircle, label: t("staff.catQuestion") },
  ];
  const PROVIDERS: { id: Provider; label: string }[] = [
    { id: "gmail", label: t("staff.providerGmail") },
    { id: "outlook", label: t("staff.providerOutlook") },
    { id: "default", label: t("staff.providerDefault") },
  ];

  const chip = (active: boolean) =>
    cn(
      "inline-flex items-center gap-1.5 border px-2.5 py-1 font-mono text-xs transition-colors",
      active
        ? "border-[var(--ring)] bg-[var(--surface-2)]"
        : "border-[var(--border)] bg-[var(--surface)] text-[var(--text-muted)] hover:text-[var(--text)]",
    );

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!message.trim()) {
      setError(t("staff.errMessage"));
      return;
    }
    setError(null);
    const catLabel = CATS.find((c) => c.id === category)!.label;
    const subj = subject.trim() ? `[${catLabel}] ${subject.trim()}` : `[${catLabel}]`;
    window.open(
      composeUrl(provider, STAFF_EMAIL, subj, message.trim()),
      "_blank",
      "noopener,noreferrer",
    );
  }

  return (
    <section>
      <SectionHeading label={t("staff.label")} desc={t("staff.desc")} />

      <Window className="retro-shadow-lg">
        <WindowBar title={t("staff.bar")} />
        <form onSubmit={handleSubmit} className="flex flex-col gap-4 p-5">
          <div className="font-mono text-[11px] text-[var(--text-muted)]">
            {t("staff.recipientLabel")}{" "}
            <span className="text-[var(--text)]">{STAFF_EMAIL}</span>
          </div>

          <div>
            <label className="mb-1 block font-mono text-xs text-[var(--text-muted)]">
              {t("staff.categoryLabel")}
            </label>
            <div className="flex flex-wrap gap-2">
              {CATS.map(({ id, icon: Icon, label }) => (
                <button
                  key={id}
                  type="button"
                  aria-pressed={category === id}
                  onClick={() => setCategory(id)}
                  className={chip(category === id)}
                >
                  <Icon className="h-3.5 w-3.5" /> {label}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="mb-1 block font-mono text-xs text-[var(--text-muted)]">
              {t("staff.subjectLabel")}
            </label>
            <Input
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              maxLength={140}
              placeholder={t("staff.subjectPlaceholder")}
            />
          </div>

          <div>
            <label className="mb-1 block font-mono text-xs text-[var(--text-muted)]">
              {t("staff.messageLabel")}
            </label>
            <Textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              rows={6}
              maxLength={4000}
              placeholder={t("staff.composerPlaceholder")}
              required
            />
          </div>

          <div>
            <label className="mb-1 block font-mono text-xs text-[var(--text-muted)]">
              {t("staff.providerLabel")}
            </label>
            <div className="flex flex-wrap gap-2">
              {PROVIDERS.map(({ id, label }) => (
                <button
                  key={id}
                  type="button"
                  aria-pressed={provider === id}
                  onClick={() => setProvider(id)}
                  className={chip(provider === id)}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          <p className="font-mono text-[11px] text-[var(--text-muted)]">
            {t("staff.handoffNote")}
          </p>

          {error && (
            <p className="font-mono text-xs text-[var(--primary)]" role="alert">
              {error}
            </p>
          )}

          <div className="flex justify-end">
            <Button type="submit">
              <Send className="h-4 w-4" /> {t("staff.sendBtn")}
            </Button>
          </div>
        </form>
      </Window>
    </section>
  );
}
