"use client";

import { useCallback, useState } from "react";
import { toast } from "sonner";
import * as api from "@/lib/api";
import type { Place } from "@/lib/types";
import { useLocalState } from "./use-local-state";

function explain(e: unknown): string {
  if (typeof GeolocationPositionError !== "undefined" && e instanceof GeolocationPositionError) {
    if (e.code === e.PERMISSION_DENIED)
      return "Location permission is blocked. Allow it in your browser's address bar, or search for your village instead.";
    if (e.code === e.TIMEOUT) return "Finding your location took too long. Please try again, or search for your village.";
    return "Your device could not find its location. Please search for your village instead.";
  }
  return e instanceof Error ? e.message : "Could not find your location.";
}

/** The farmer's saved place (persisted), plus one-tap "use my current location" via GPS. */
export function usePlace() {
  const [place, setPlace] = useLocalState<Place | null>("kisanmitra.place", null);
  const [locating, setLocating] = useState(false);

  /** Asks the browser for GPS, converts it to a village/district/state. Returns the place, or null on failure. */
  const detect = useCallback(async (): Promise<Place | null> => {
    if (typeof navigator === "undefined" || !("geolocation" in navigator)) {
      toast.error("This browser cannot share your location. Please search for your village instead.");
      return null;
    }
    if (!window.isSecureContext) {
      toast.error("Location needs a secure (https) connection. Please search for your village instead.");
      return null;
    }
    setLocating(true);
    try {
      const pos = await new Promise<GeolocationPosition>((resolve, reject) =>
        navigator.geolocation.getCurrentPosition(resolve, reject, {
          enableHighAccuracy: false, // village-level is enough for weather, and is much faster
          timeout: 12000,
          maximumAge: 5 * 60 * 1000,
        }),
      );
      const found = await api.reversePlace(pos.coords.latitude, pos.coords.longitude);
      setPlace(found);
      toast.success(`Location set: ${found.label ?? found.name}`);
      return found;
    } catch (e) {
      toast.error(explain(e));
      return null;
    } finally {
      setLocating(false);
    }
  }, [setPlace]);

  return { place, setPlace, detect, locating };
}
