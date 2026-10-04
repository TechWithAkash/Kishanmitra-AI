"use client";

import { useCallback, useEffect, useState } from "react";

/** useState that persists to localStorage (hydrated after mount, so SSR-safe). */
export function useLocalState<T>(key: string, initial: T) {
  const [value, setValue] = useState<T>(initial);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(key);
      // Hydrate after mount: localStorage does not exist during server rendering.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      if (raw !== null) setValue(JSON.parse(raw) as T);
    } catch {}
  }, [key]);

  const set = useCallback(
    (next: T) => {
      setValue(next);
      try {
        localStorage.setItem(key, JSON.stringify(next));
      } catch {}
    },
    [key],
  );

  return [value, set] as const;
}
