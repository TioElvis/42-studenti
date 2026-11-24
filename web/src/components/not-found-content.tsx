"use client";

import Link from "next/link";
import { CalendarDays, FileQuestion, Home } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Window, WindowBar } from "@/components/ui/card";
import { useI18n } from "@/providers/i18n-provider";

/** The 404 body (client) — translated and theme-reactive. */
export function NotFoundContent() {
  const { t } = useI18n();
  return (
    <section className="flex flex-col items-center py-6">
      <Window className="retro-shadow-lg w-full max-w-xl">
        <WindowBar title={t("notFound.bar")}>
          <span>{t("notFound.barSub")}</span>
        </WindowBar>

        <div className="flex flex-col items-center gap-5 p-8 text-center">
          <div
            className="flex items-center gap-3 font-display font-bold leading-none"
            style={{ color: "var(--primary)" }}
          >
            <FileQuestion className="h-9 w-9 sm:h-10 sm:w-10" aria-hidden />
            <span className="text-6xl tracking-tight sm:text-7xl">404</span>
          </div>

          <div>
            <h1 className="font-display text-2xl font-bold">
              {t("notFound.title")}
              <span className="cursor-blink" aria-hidden>
                _
              </span>
            </h1>
            <p className="mx-auto mt-2 max-w-sm font-mono text-sm text-[var(--text-muted)]">
              {t("notFound.body")}
            </p>
          </div>

          {/* Faux terminal readout for the retro vibe. */}
          <div className="w-full border border-[var(--border-subtle)] bg-[var(--surface-sunken)] p-3 text-left font-mono text-xs rounded-[var(--radius-inner)]">
            <div className="text-[var(--text-muted)]">{t("notFound.term1")}</div>
            <div className="text-[var(--primary)]">{t("notFound.term2")}</div>
          </div>

          <div className="flex flex-wrap items-center justify-center gap-2">
            <Button asChild>
              <Link href="/">
                <Home className="h-4 w-4" /> {t("notFound.home")}
              </Link>
            </Button>
            <Button asChild variant="outline">
              <Link href="/eventi">
                <CalendarDays className="h-4 w-4" /> {t("notFound.events")}
              </Link>
            </Button>
          </div>
        </div>
      </Window>
    </section>
  );
}
