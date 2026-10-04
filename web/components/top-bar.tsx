"use client";

import { useTheme } from "@/components/theme-provider";
import { AnimatedThemeToggler } from "@/components/ui/animated-theme-toggler";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { SidebarTrigger } from "@/components/ui/sidebar";
import { LocationPicker } from "@/components/location-picker";
import { LANGUAGES } from "@/lib/languages";
import type { Place } from "@/lib/types";

function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  return (
    <AnimatedThemeToggler
      theme={resolvedTheme === "dark" ? "dark" : "light"}
      onThemeChange={setTheme}
      aria-label="Toggle theme"
      className="grid size-8 place-items-center rounded-lg hover:bg-muted [&_svg]:size-4"
    />
  );
}

export function TopBar({
  langPref,
  onLangChange,
  place,
  onPlaceChange,
  onDetect,
  locating,
}: {
  langPref: string;
  onLangChange: (v: string) => void;
  place: Place | null;
  onPlaceChange: (p: Place | null) => void;
  onDetect: () => Promise<Place | null>;
  locating: boolean;
}) {
  return (
    <header className="flex h-14 shrink-0 items-center gap-2 border-b px-3">
      <SidebarTrigger />
      <Select value={langPref} onValueChange={(v) => v && onLangChange(v)}>
        <SelectTrigger size="sm" aria-label="Reply language" className="w-40">
          <SelectValue>{(v: string) => LANGUAGES.find((l) => l.code === v)?.native ?? v}</SelectValue>
        </SelectTrigger>
        <SelectContent>
          {LANGUAGES.map((l) => (
            <SelectItem key={l.code} value={l.code}>
              {l.native}
              {l.code !== "auto" && l.native !== l.label && (
                <span className="text-muted-foreground"> · {l.label}</span>
              )}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <LocationPicker place={place} onChange={onPlaceChange} onDetect={onDetect} locating={locating} />
      <div className="ml-auto">
        <ThemeToggle />
      </div>
    </header>
  );
}
