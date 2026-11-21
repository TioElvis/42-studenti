"use client";

import { Folder, Megaphone, Presentation, FileText, Lock } from "lucide-react";

import { SectionHeading } from "@/components/chrome/section-heading";
import { Window, WindowBar } from "@/components/ui/card";
import { useI18n } from "@/providers/i18n-provider";

export function ArchivioComingSoon() {
  const { t } = useI18n();

  const entries = [
    { icon: Folder, name: "riepiloghi_eventi/", kind: "<DIR>", desc: t("archivio.e1") },
    { icon: Megaphone, name: "comunicazioni/", kind: "<DIR>", desc: t("archivio.e2") },
    { icon: Presentation, name: "slide_e_ppt/", kind: "<DIR>", desc: t("archivio.e3") },
    { icon: FileText, name: "materiali_campus/", kind: "<DIR>", desc: t("archivio.e4") },
  ];

  return (
    <section>
      <SectionHeading label={t("archivio.label")} desc={t("archivio.desc")} />

      <Window className="retro-shadow-lg">
        <WindowBar title={t("archivio.bar")}>
          <span>{t("archivio.barSub")}</span>
        </WindowBar>

        {/* A retro directory listing of what will live here (all locked for now). */}
        <div className="p-4 font-mono text-sm">
          <div className="mb-3 text-[var(--text-muted)]">
            C:\42ROMA\ARCHIVIO&gt; dir<span className="cursor-blink">_</span>
          </div>

          <ul className="flex flex-col">
            {entries.map(({ icon: Icon, name, kind, desc }) => (
              <li
                key={name}
                className="flex items-center gap-3 border-b border-dashed border-[var(--border-subtle)] py-2.5 last:border-b-0"
              >
                <Icon className="h-4 w-4 shrink-0 text-[var(--text-muted)]" aria-hidden />
                <span className="w-10 shrink-0 text-[11px] text-[var(--text-muted)]">{kind}</span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate font-bold">{name}</span>
                  <span className="block truncate text-[11px] text-[var(--text-muted)]">
                    {desc}
                  </span>
                </span>
                <span className="inline-flex shrink-0 items-center gap-1 border border-[var(--border)] bg-[var(--surface-2)] px-2 py-0.5 text-[10px] text-[var(--text-muted)]">
                  <Lock className="h-3 w-3" /> {t("archivio.locked")}
                </span>
              </li>
            ))}
          </ul>

          <div className="mt-4 border-t border-[var(--border)] pt-3 text-[11px] text-[var(--text-muted)]">
            {t("archivio.footerLine")}
          </div>
        </div>
      </Window>

      <p
        className="mt-4 border px-4 py-2 text-center font-mono text-sm"
        style={{
          borderColor: "var(--cat-vita_romana-fg)",
          background: "var(--cat-vita_romana-bg)",
          color: "var(--cat-vita_romana-fg)",
        }}
      >
        {t("archivio.banner")}
      </p>
    </section>
  );
}
