"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

type Theme = "light" | "dark" | "system";
type Resolved = "light" | "dark";

const KEY = "theme";

type Ctx = { theme: Theme; resolvedTheme: Resolved; systemTheme: Resolved; setTheme: (t: Theme) => void };
const ThemeContext = createContext<Ctx | null>(null);

/**
 * Runs before first paint (inlined in <head> by the root layout) so the page never flashes the
 * wrong theme. It lives in a server component on purpose: React 19 warns about <script> tags
 * rendered by client components, which is what the `next-themes` package does.
 */
export const THEME_INIT_SCRIPT = `try{var t=localStorage.getItem("${KEY}")||"system";var d=t==="dark"||(t==="system"&&matchMedia("(prefers-color-scheme: dark)").matches);document.documentElement.classList.toggle("dark",d);document.documentElement.style.colorScheme=d?"dark":"light"}catch(e){}`;

const systemPref = (): Resolved =>
  typeof matchMedia !== "undefined" && matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";

/** Light/dark/system theme with the same API as `next-themes` (useTheme), minus the script tag. */
export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = useState<Theme>("system");
  const [systemTheme, setSystemTheme] = useState<Resolved>("light");

  useEffect(() => {
    // Hydrate from localStorage / the OS after mount (neither exists during server rendering).
    /* eslint-disable react-hooks/set-state-in-effect */
    try {
      const saved = localStorage.getItem(KEY);
      if (saved === "light" || saved === "dark" || saved === "system") setThemeState(saved);
    } catch {}
    setSystemTheme(systemPref());
    /* eslint-enable react-hooks/set-state-in-effect */

    const mql = matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => setSystemTheme(systemPref());
    mql.addEventListener("change", onChange);
    return () => mql.removeEventListener("change", onChange);
  }, []);

  const resolvedTheme: Resolved = theme === "system" ? systemTheme : theme;

  useEffect(() => {
    document.documentElement.classList.toggle("dark", resolvedTheme === "dark");
    document.documentElement.style.colorScheme = resolvedTheme;
  }, [resolvedTheme]);

  const setTheme = useCallback((t: Theme) => {
    setThemeState(t);
    try {
      localStorage.setItem(KEY, t);
    } catch {}
  }, []);

  const value = useMemo(() => ({ theme, resolvedTheme, systemTheme, setTheme }), [theme, resolvedTheme, systemTheme, setTheme]);
  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): Ctx {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme must be used inside <ThemeProvider>");
  return ctx;
}
