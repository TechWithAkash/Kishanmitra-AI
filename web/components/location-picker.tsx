"use client";

import { useEffect, useRef, useState } from "react";
import { Check, ChevronsUpDown, Loader2, LocateFixed, MapPin, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { searchPlaces } from "@/lib/api";
import type { Place } from "@/lib/types";

/** Pick where you are: GPS in one tap, or search any village, town or district in India. */
export function LocationPicker({
  place,
  onChange,
  onDetect,
  locating,
}: {
  place: Place | null;
  onChange: (p: Place | null) => void;
  onDetect: () => Promise<Place | null>;
  locating: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Place[]>([]);
  const [searching, setSearching] = useState(false);
  const [failed, setFailed] = useState(false);
  const seq = useRef(0);

  // Search as you type (debounced); stale responses are ignored.
  useEffect(() => {
    const q = query.trim();
    if (q.length < 2) return;
    const mine = ++seq.current;
    const controller = new AbortController();
    const timer = setTimeout(async () => {
      setSearching(true);
      try {
        const found = await searchPlaces(q, controller.signal);
        if (mine === seq.current) {
          setResults(found);
          setFailed(false);
        }
      } catch {
        if (mine === seq.current && !controller.signal.aborted) {
          setResults([]);
          setFailed(true);
        }
      } finally {
        if (mine === seq.current) setSearching(false);
      }
    }, 300);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [query]);

  const shown = query.trim().length >= 2 ? results : [];
  const choose = (p: Place | null) => {
    onChange(p);
    setOpen(false);
    setQuery("");
  };

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger render={<Button variant="outline" size="sm" aria-label="My location" className="gap-1.5" />}>
        {locating ? <Loader2 className="animate-spin" /> : <MapPin className={place ? "text-primary" : undefined} />}
        <span className="max-w-32 truncate">{place ? (place.label ?? place.name) : "Set location"}</span>
        <ChevronsUpDown className="opacity-50" />
      </PopoverTrigger>
      <PopoverContent className="w-80 p-0" align="start">
        <Command shouldFilter={false}>
          <CommandInput value={query} onValueChange={setQuery} placeholder="Search village, town or district…" />
          <CommandList>
            <CommandGroup>
              <CommandItem
                onSelect={async () => {
                  const p = await onDetect();
                  if (p) setOpen(false);
                }}
                disabled={locating}
              >
                {locating ? <Loader2 className="animate-spin" /> : <LocateFixed className="text-primary" />}
                <span className="font-medium">Use my current location</span>
              </CommandItem>
              {place && (
                <CommandItem onSelect={() => choose(null)}>
                  <X />
                  Clear location
                </CommandItem>
              )}
            </CommandGroup>
            {query.trim().length < 2 && (
              <p className="px-3 pt-1 pb-3 text-xs text-muted-foreground">
                Or type the name of your village, town or district. Weather and mandi prices will be for that place.
              </p>
            )}
            {searching && (
              <p className="flex items-center gap-2 px-3 py-3 text-sm text-muted-foreground" role="status">
                <Loader2 className="size-4 animate-spin" /> Searching…
              </p>
            )}
            {!searching && query.trim().length >= 2 && shown.length === 0 && (
              <CommandEmpty>
                {failed ? "Search is unavailable right now. Try again, or use your current location." : "No place found. Try a nearby town."}
              </CommandEmpty>
            )}
            {shown.length > 0 && (
              <CommandGroup heading="Places">
                {shown.map((p) => (
                  <CommandItem key={`${p.lat}-${p.lon}`} value={`${p.lat}-${p.lon}`} onSelect={() => choose(p)}>
                    <MapPin />
                    <span className="truncate">{p.label ?? p.name}</span>
                    {place && place.lat === p.lat && place.lon === p.lon && <Check className="ml-auto" />}
                  </CommandItem>
                ))}
              </CommandGroup>
            )}
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
