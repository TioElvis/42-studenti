"use client";

import Link from "next/link";
import { LogOut } from "lucide-react";

import { Avatar } from "./avatar";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/providers/auth-provider";
import { useI18n } from "@/providers/i18n-provider";

export function UserMenu() {
  const { user, logout } = useAuth();
  const { t } = useI18n();
  if (!user) return null;

  return (
    <div className="flex items-center gap-2">
      <Link
        href={`/u/${user.login}`}
        title={t("profile.myProfile")}
        className="hidden items-center gap-2 border border-[var(--border)] bg-[var(--surface)] px-2 py-1 retro-shadow-sm transition-colors hover:bg-[var(--surface-2)] sm:inline-flex"
      >
        <Avatar user={user} size={24} />
        <span className="font-mono text-xs">@{user.login}</span>
      </Link>
      <Button variant="outline" size="icon" aria-label={t("userMenu.logout")} onClick={() => void logout()}>
        <LogOut className="h-4 w-4" />
      </Button>
    </div>
  );
}
