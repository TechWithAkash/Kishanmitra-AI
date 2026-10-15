"use client";

import { motion } from "motion/react";
import { cn } from "@/lib/utils";
import { pct } from "@/lib/metrics";

/** One labelled horizontal bar whose width animates in. `value` is 0..1. */
export function Bar({ label, value, note, tone = "primary", suffix }: {
  label: string;
  value: number;
  note?: string;
  tone?: "primary" | "amber" | "sky" | "muted";
  suffix?: string;
}) {
  const color = { primary: "bg-primary", amber: "bg-amber-500", sky: "bg-sky-500", muted: "bg-muted-foreground/40" }[tone];
  return (
    <div className="flex items-center gap-3 text-sm">
      <span className="w-40 shrink-0 truncate sm:w-56" title={label}>{label}</span>
      <div className="relative h-3 flex-1 overflow-hidden rounded-full bg-muted" role="img" aria-label={`${label}: ${pct(value)}`}>
        <motion.div
          className={cn("h-full rounded-full", color)}
          initial={{ width: 0 }}
          animate={{ width: `${Math.max(0, Math.min(1, value)) * 100}%` }}
          transition={{ duration: 0.7, ease: "easeOut" }}
        />
      </div>
      <span className="w-20 shrink-0 text-right font-medium tabular-nums">{suffix ?? pct(value)}</span>
      {note && <span className="hidden w-24 shrink-0 text-xs text-muted-foreground tabular-nums md:block">{note}</span>}
    </div>
  );
}
