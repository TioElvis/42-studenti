"use client";

import * as React from "react";

import { useAuth } from "@/providers/auth-provider";
import { useI18n } from "@/providers/i18n-provider";
import { BootScreen } from "@/components/chrome/boot-screen";
import { WakeScreen } from "@/components/chrome/wake-screen";
import { LoginGate } from "@/components/login-gate";
import { TopRibbon } from "@/components/chrome/top-ribbon";
import { Brand } from "@/components/chrome/brand";
import { StatusPill } from "@/components/chrome/status-pill";
import { NavTabs } from "@/components/chrome/nav-tabs";
import { SettingsModal } from "@/components/chrome/settings-modal";
import { UserMenu } from "@/components/chrome/user-menu";
import { NotificationBell } from "@/components/notifications/notification-bell";

/**
 * The authentication gate. Unauthenticated visitors only ever see <LoginGate>;
 * the protected sections (children) render only for a logged-in 42 student.
 */
export function AppFrame({ children }: { children: React.ReactNode }) {
  const { status } = useAuth();
  const { t } = useI18n();

  if (status === "loading") {
    return <BootScreen />;
  }

  // The API is asleep / unreachable: a dedicated page until it answers.
  if (status === "waking") {
    return <WakeScreen />;
  }

  if (status === "anonymous") {
    return (
      <React.Suspense fallback={<BootScreen />}>
        <LoginGate />
      </React.Suspense>
    );
  }

  return (
    <div className="flex min-h-screen flex-col">
      <TopRibbon />
      <header className="mx-auto flex w-full max-w-5xl flex-wrap items-center justify-between gap-3 px-4 pt-6">
        <Brand />
        <div className="flex items-center gap-2">
          <span className="hidden md:inline-flex">
            <StatusPill />
          </span>
          <NotificationBell />
          <SettingsModal compact />
          <UserMenu />
        </div>
      </header>
      <div className="mx-auto w-full max-w-5xl px-4 py-3">
        <NavTabs />
      </div>
      <main className="mx-auto w-full max-w-5xl flex-1 px-4 pb-20 pt-2">{children}</main>
      <footer className="mt-auto border-t border-[var(--border)] bg-[var(--surface)] py-5">
        <div className="mx-auto max-w-5xl px-4 text-center font-mono text-[11px] text-[var(--text-muted)]">
          {t("footer")}
        </div>
      </footer>
    </div>
  );
}
