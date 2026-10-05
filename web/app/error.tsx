"use client";

import { useEffect } from "react";
import { Button } from "@/components/ui/button";

/** Shown instead of a blank page if something unexpected breaks while using the app. */
export default function Error({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <main className="grid min-h-dvh place-items-center p-6">
      <div className="flex max-w-sm flex-col items-center gap-4 text-center">
        <span className="text-5xl" aria-hidden>
          🌾
        </span>
        <h1 className="text-xl font-semibold">Something went wrong</h1>
        <p className="text-sm text-muted-foreground">
          Sorry about that. Your chats are saved on this device. Please try again.
        </p>
        <Button onClick={reset}>Try again</Button>
      </div>
    </main>
  );
}
