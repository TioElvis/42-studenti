"use client";

import * as React from "react";

export type Theme = "classic" | "hacker" | "bento" | "bento-hacker";

/** All supported themes, in cycle order. */
export const THEMES: Theme[] = ["classic", "hacker", "bento", "bento-hacker"];

const STORAGE_KEY = "42roma.theme";
const DEFAULT_THEME: Theme = "classic";

interface ThemeContextValue {
  theme: Theme;
  setTheme: (t: Theme) => void;
  toggleTheme: () => void;
}

const ThemeContext = React.createContext<ThemeContextValue | null>(null);

/** Inline script (runs before paint) that applies the stored theme with no flash. */
export const themeInitScript = `
(function(){try{var ts=${JSON.stringify(THEMES)};var t=localStorage.getItem(${JSON.stringify(STORAGE_KEY)});
if(ts.indexOf(t)===-1){t=${JSON.stringify(DEFAULT_THEME)};}
document.documentElement.setAttribute("data-theme",t);}catch(e){
document.documentElement.setAttribute("data-theme",${JSON.stringify(DEFAULT_THEME)});}})();
`;

function isTheme(v: unknown): v is Theme {
  return typeof v === "string" && (THEMES as string[]).includes(v);
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = React.useState<Theme>(DEFAULT_THEME);

  React.useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (isTheme(stored)) {
        setThemeState(stored);
      }
    } catch {
      /* localStorage unavailable (private mode) — keep the default. */
    }
  }, []);

  const setTheme = React.useCallback((t: Theme) => {
    setThemeState(t);
    document.documentElement.setAttribute("data-theme", t);
    try {
      localStorage.setItem(STORAGE_KEY, t);
    } catch {
      /* ignore persistence failures */
    }
  }, []);

  const toggleTheme = React.useCallback(() => {
    const i = THEMES.indexOf(theme);
    setTheme(THEMES[(i + 1) % THEMES.length]!);
  }, [theme, setTheme]);

  const value = React.useMemo(
    () => ({ theme, setTheme, toggleTheme }),
    [theme, setTheme, toggleTheme],
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
  const ctx = React.useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme must be used within <ThemeProvider>");
  return ctx;
}
