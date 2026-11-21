"use client";

import { Window, WindowBar } from "@/components/ui/card";
import { useI18n } from "@/providers/i18n-provider";

/** Retro-window hero with the pixel-art Rome banner and Ken Burns pan. */
export function Hero() {
  const { t } = useI18n();
  return (
    <Window className="retro-shadow mb-8 overflow-hidden">
      <WindowBar title="ROMA_PIXEL.BMP — 320x160" />
      <div className="relative h-44 overflow-hidden border-b border-[var(--border)] sm:h-56">
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
              "linear-gradient(to top, color-mix(in srgb, var(--bg) 80%, transparent), transparent 60%)",
          }}
        />
        <div className="absolute bottom-3 left-4 right-4">
          <h1 className="font-display text-2xl font-bold text-white drop-shadow-[2px_2px_0_rgba(0,0,0,0.6)] sm:text-3xl">
            {t("hero.title")}
          </h1>
          <p className="font-mono text-sm text-white/90 drop-shadow-[1px_1px_0_rgba(0,0,0,0.6)]">
            {t("hero.subtitle")}
          </p>
        </div>
        <div
          className="absolute right-3 top-3 rotate-6 border px-2 py-1 font-display text-[10px] font-bold"
          style={{
            background: "var(--primary)",
            color: "var(--primary-fg)",
            borderColor: "var(--border)",
            boxShadow: "2px 2px 0 rgba(0,0,0,0.4)",
          }}
        >
          {t("hero.stamp")}
        </div>
      </div>
    </Window>
  );
}
