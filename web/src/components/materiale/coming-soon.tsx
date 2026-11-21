"use client";

import { GitBranch, BookOpen, Link2, FlaskConical, Lock } from "lucide-react";

import { SectionHeading } from "@/components/chrome/section-heading";
import { Window, WindowBar } from "@/components/ui/card";
import { useI18n } from "@/providers/i18n-provider";

export function MaterialeComingSoon() {
  const { t } = useI18n();

  // A taste of what students will be able to link here (repos, guides, resources).
  const entries = [
    { icon: GitBranch, project: "libft", desc: t("materiale.e1") },
    { icon: FlaskConical, project: "ft_printf / get_next_line", desc: t("materiale.e2") },
    { icon: BookOpen, project: "minishell", desc: t("materiale.e3") },
    { icon: Link2, project: "cub3d / miniRT", desc: t("materiale.e4") },
  ];

  return (
    <section>
      <SectionHeading label={t("materiale.label")} desc={t("materiale.desc")} />

      <Window className="retro-shadow-lg">
        <WindowBar title={t("materiale.bar")}>
          <span>{t("materiale.barSub")}</span>
        </WindowBar>

        <div className="p-4 font-mono text-sm">
          <div className="mb-3 text-[var(--text-muted)]">
            $ git clone 42roma://materiale-didattico<span className="cursor-blink">_</span>
          </div>

          <ul className="flex flex-col">
            {entries.map(({ icon: Icon, project, desc }) => (
              <li
                key={project}
                className="flex items-center gap-3 border-b border-dashed border-[var(--border-subtle)] py-2.5 last:border-b-0"
              >
                <Icon className="h-4 w-4 shrink-0 text-[var(--text-muted)]" aria-hidden />
                <span className="min-w-0 flex-1">
                  <span className="block truncate font-bold">{project}</span>
                  <span className="block truncate text-[11px] text-[var(--text-muted)]">{desc}</span>
                </span>
                <span className="inline-flex shrink-0 items-center gap-1 border border-[var(--border)] bg-[var(--surface-2)] px-2 py-0.5 text-[10px] text-[var(--text-muted)]">
                  <Lock className="h-3 w-3" /> {t("materiale.locked")}
                </span>
              </li>
            ))}
          </ul>

          <div className="mt-4 border-t border-[var(--border)] pt-3 text-[11px] text-[var(--text-muted)]">
            {t("materiale.footerLine")}
          </div>
        </div>
      </Window>

      <p
        className="mt-4 border px-4 py-2 text-center font-mono text-sm"
        style={{
          borderColor: "var(--cat-studio-fg)",
          background: "var(--cat-studio-bg)",
          color: "var(--cat-studio-fg)",
        }}
      >
        {t("materiale.banner")}
      </p>
    </section>
  );
}
