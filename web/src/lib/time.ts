/** Relative timestamps and retro date/time helpers, in Italian or English. */

import type { Lang } from "./messages";

const RT = {
  it: {
    now: "proprio ora",
    min1: "un minuto fa",
    minN: (n: number) => `${n} minuti fa`,
    hour1: "un'ora fa",
    hourN: (n: number) => `${n} ore fa`,
    yesterday: "ieri",
    dayN: (n: number) => `${n} giorni fa`,
    month1: "un mese fa",
    monthN: (n: number) => `${n} mesi fa`,
    year1: "un anno fa",
    yearN: (n: number) => `${n} anni fa`,
  },
  en: {
    now: "just now",
    min1: "a minute ago",
    minN: (n: number) => `${n} minutes ago`,
    hour1: "an hour ago",
    hourN: (n: number) => `${n} hours ago`,
    yesterday: "yesterday",
    dayN: (n: number) => `${n} days ago`,
    month1: "a month ago",
    monthN: (n: number) => `${n} months ago`,
    year1: "a year ago",
    yearN: (n: number) => `${n} years ago`,
  },
} as const;

export function relativeTime(iso: string, lang: Lang = "it"): string {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "";
  const seconds = Math.floor((Date.now() - then) / 1000);
  const r = RT[lang];

  if (seconds < 45) return r.now;
  if (seconds < 90) return r.min1;

  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return r.minN(minutes);

  const hours = Math.floor(minutes / 60);
  if (hours < 24) return hours === 1 ? r.hour1 : r.hourN(hours);

  const days = Math.floor(hours / 24);
  if (days === 1) return r.yesterday;
  if (days < 30) return r.dayN(days);

  const months = Math.floor(days / 30);
  if (months < 12) return months === 1 ? r.month1 : r.monthN(months);

  const years = Math.floor(days / 365);
  return years === 1 ? r.year1 : r.yearN(years);
}

const MONTHS: Record<Lang, string[]> = {
  it: ["GEN", "FEB", "MAR", "APR", "MAG", "GIU", "LUG", "AGO", "SET", "OTT", "NOV", "DIC"],
  en: ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"],
};

/** Split a date into a retro day/month block for event cards. */
export function dateBlock(iso: string | null, lang: Lang = "it"): { day: string; month: string } {
  if (!iso) return { day: "--", month: "---" };
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return { day: "--", month: "---" };
  return {
    day: String(d.getDate()).padStart(2, "0"),
    month: MONTHS[lang][d.getMonth()] ?? "---",
  };
}

const LOCALE: Record<Lang, string> = { it: "it-IT", en: "en-GB" };

/** Time range like "14:00 – 18:00" (or just the start). */
export function timeRange(begin: string | null, end: string | null, lang: Lang = "it"): string {
  const fmt = (iso: string | null) => {
    if (!iso) return "";
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return "";
    return d.toLocaleTimeString(LOCALE[lang], { hour: "2-digit", minute: "2-digit" });
  };
  const a = fmt(begin);
  const b = fmt(end);
  if (a && b) return `${a} – ${b}`;
  return a || b || "";
}

/** Full, human date like "lunedì 5 maggio 2025" / "Monday, 5 May 2025". */
export function fullDate(iso: string | null, lang: Lang = "it"): string | null {
  if (!iso) return null;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return null;
  return d.toLocaleDateString(LOCALE[lang], {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}
