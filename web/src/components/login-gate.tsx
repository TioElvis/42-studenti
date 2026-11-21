"use client";

import * as React from "react";
import { useSearchParams } from "next/navigation";

import { Window, WindowBar } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { SettingsModal } from "@/components/chrome/settings-modal";
import { TopRibbon } from "@/components/chrome/top-ribbon";
import { StatusPill } from "@/components/chrome/status-pill";
import { useI18n } from "@/providers/i18n-provider";
import { loginUrl } from "@/lib/api";

const AUTH_ERROR_KEYS: Record<string, string> = {
  state: "login.errState",
  oauth: "login.errOauth",
  denied: "login.errDenied",
  config: "login.errConfig",
  campus: "login.errCampus",
};

/** The strict login gate: the only thing an anonymous visitor can see. */
export function LoginGate() {
  const params = useSearchParams();
  const { t } = useI18n();
  const errKey = params.get("auth_error");
  const errMsg = errKey ? t(AUTH_ERROR_KEYS[errKey] ?? "login.errOauth") : null;

  return (
    <div className="min-h-screen">
      <TopRibbon />
      <div className="mx-auto flex max-w-md flex-col items-stretch gap-4 px-4 py-10 sm:py-16">
        <div className="flex items-center justify-between">
          <StatusPill />
          <SettingsModal compact />
        </div>

        <Window className="retro-shadow-lg overflow-hidden fade-up">
          <WindowBar title="ACCEDI_AL_CAMPUS.EXE" />
          <div className="relative h-36 overflow-hidden border-b border-[var(--border)]">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src="/rome-pixel.png"
              alt="Veduta pixel-art di Roma"
              className="ken-burns absolute inset-0 h-full w-full object-cover"
              style={{ imageRendering: "pixelated" }}
            />
            <div
              className="absolute inset-0"
              style={{
                background:
                  "linear-gradient(to top, color-mix(in srgb, var(--bg) 85%, transparent), transparent 55%)",
              }}
            />
            <div
              className="absolute right-2 top-2 rotate-6 border px-2 py-0.5 font-display text-[9px] font-bold"
              style={{
                background: "var(--primary)",
                color: "var(--primary-fg)",
                borderColor: "var(--border)",
              }}
            >
              SPQR
            </div>
          </div>

          <div className="flex flex-col gap-4 p-6 text-center">
            <div>
              <h1 className="font-display text-2xl font-bold">
                42 Studenti<span className="cursor-blink">_</span>
              </h1>
              <p className="mt-2 font-mono text-sm text-[var(--text-muted)]">{t("login.subtitle")}</p>
            </div>

            {errMsg && (
              <p
                className="border px-3 py-2 text-sm"
                style={{
                  borderColor: "var(--primary)",
                  background: "color-mix(in srgb, var(--primary) 12%, transparent)",
                  color: "var(--primary)",
                }}
                role="alert"
              >
                {errMsg}
              </p>
            )}

            <Button asChild size="lg" className="w-full justify-center text-base">
              <a href={loginUrl()}>
                <span className="font-display">&gt;</span> {t("login.button")}
              </a>
            </Button>

            <p className="font-mono text-[11px] text-[var(--text-muted)]">{t("login.footer")}</p>
          </div>
        </Window>
      </div>
    </div>
  );
}
