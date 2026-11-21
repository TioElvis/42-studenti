"use client";

import * as React from "react";

import { messages, type Lang } from "@/lib/messages";

const STORAGE_KEY = "42roma.lang";
const DEFAULT_LANG: Lang = "it";

type Vars = Record<string, string | number>;

interface I18nContextValue {
  lang: Lang;
  setLang: (l: Lang) => void;
  toggleLang: () => void;
  /** Resolve a dot-path key in the current language ({var} tokens interpolated). */
  t: (key: string, vars?: Vars) => string;
}

const I18nContext = React.createContext<I18nContextValue | null>(null);

function resolve(lang: Lang, key: string): string | undefined {
  let node: unknown = messages[lang];
  for (const part of key.split(".")) {
    if (node == null || typeof node !== "object") return undefined;
    node = (node as Record<string, unknown>)[part];
  }
  return typeof node === "string" ? node : undefined;
}

function interpolate(s: string, vars?: Vars): string {
  if (!vars) return s;
  return s.replace(/\{(\w+)\}/g, (_, k) => (k in vars ? String(vars[k]) : `{${k}}`));
}

export function I18nProvider({ children }: { children: React.ReactNode }) {
  const [lang, setLangState] = React.useState<Lang>(DEFAULT_LANG);

  React.useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored === "it" || stored === "en") setLangState(stored);
    } catch {
      /* localStorage unavailable (private mode) — keep the default. */
    }
  }, []);

  React.useEffect(() => {
    try {
      document.documentElement.lang = lang;
    } catch {
      /* ignore */
    }
  }, [lang]);

  const setLang = React.useCallback((l: Lang) => {
    setLangState(l);
    try {
      localStorage.setItem(STORAGE_KEY, l);
    } catch {
      /* ignore persistence failures */
    }
  }, []);

  const toggleLang = React.useCallback(
    () => setLang(lang === "it" ? "en" : "it"),
    [lang, setLang],
  );

  const t = React.useCallback(
    (key: string, vars?: Vars) =>
      interpolate(resolve(lang, key) ?? resolve(DEFAULT_LANG, key) ?? key, vars),
    [lang],
  );

  const value = React.useMemo(
    () => ({ lang, setLang, toggleLang, t }),
    [lang, setLang, toggleLang, t],
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18nContextValue {
  const ctx = React.useContext(I18nContext);
  if (!ctx) throw new Error("useI18n must be used within <I18nProvider>");
  return ctx;
}
