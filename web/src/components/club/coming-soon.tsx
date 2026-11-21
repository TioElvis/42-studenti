"use client";

import { Cpu, Music, MapPin, Hammer } from "lucide-react";

import { SectionHeading } from "@/components/chrome/section-heading";
import { Window, WindowBar } from "@/components/ui/card";
import { useI18n } from "@/providers/i18n-provider";

export function ClubComingSoon() {
  const { t } = useI18n();

  const preview = [
    { icon: Cpu, name: "Tech", desc: t("club.techDesc") },
    { icon: Music, name: t("club.musicName"), desc: t("club.musicDesc") },
    { icon: MapPin, name: t("club.romeName"), desc: t("club.romeDesc") },
  ];

  return (
    <section>
      <SectionHeading label={t("club.label")} desc={t("club.desc")} />

      <Window className="retro-shadow-lg mb-6 overflow-hidden">
        <WindowBar title="WORK_IN_PROGRESS.EXE" />
        <div className="flex flex-col items-center gap-3 px-6 py-10 text-center">
          <div
            className="flex h-14 w-14 items-center justify-center border border-[var(--border)] bg-[var(--surface-2)]"
            aria-hidden
          >
            <Hammer className="h-7 w-7" />
          </div>
          <h3 className="font-display text-2xl font-bold">
            {t("club.soonTitle")}
            <span className="cursor-blink">_</span>
          </h3>
          <p
            className="max-w-md border px-4 py-2 font-mono text-sm"
            style={{
              borderColor: "var(--cat-evento_casuale-fg)",
              background: "var(--cat-evento_casuale-bg)",
              color: "var(--cat-evento_casuale-fg)",
            }}
          >
            {t("club.banner")}
          </p>
        </div>
      </Window>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {preview.map(({ icon: Icon, name, desc }, i) => (
          <div
            key={name}
            className="window retro-shadow hover-lift fade-up p-5"
            style={{ animationDelay: `${i * 70}ms` }}
          >
            <div className="mb-3 flex items-center justify-between">
              <Icon className="h-6 w-6" aria-hidden />
              <span className="border border-[var(--border)] bg-[var(--surface-2)] px-2 py-0.5 font-mono text-[10px] text-[var(--text-muted)]">
                SOON
              </span>
            </div>
            <h4 className="font-display text-lg font-bold">{name}</h4>
            <p className="mt-1 text-sm text-[var(--text-muted)]">{desc}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
