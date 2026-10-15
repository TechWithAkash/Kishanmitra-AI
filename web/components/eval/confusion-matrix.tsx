"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";

const NICE: Record<string, string> = { crop_disease: "Crop problem", market_price: "Price", weather: "Weather", general: "General" };
const label = (l: string) => NICE[l] ?? l;

/**
 * Confusion matrix as a heat map. Rows are the TRUE class, columns what the model PREDICTED.
 * The diagonal is "got it right"; every other cell is a specific kind of mistake. Hover for the numbers,
 * click a cell to list those sentences.
 */
export function ConfusionMatrix({
  labels,
  matrix,
  onSelect,
  selected,
}: {
  labels: string[];
  matrix: number[][];
  onSelect?: (trueLabel: string, predLabel: string) => void;
  selected?: { t: string; p: string } | null;
}) {
  const [hover, setHover] = useState<{ t: number; p: number } | null>(null);
  const rowTotals = matrix.map((r) => r.reduce((a, b) => a + b, 0));
  const hovered = hover ? { count: matrix[hover.t][hover.p], total: rowTotals[hover.t] } : null;

  return (
    <div className="flex flex-col gap-3">
      <div className="overflow-x-auto">
        <div className="inline-grid min-w-full gap-1" style={{ gridTemplateColumns: `auto repeat(${labels.length}, minmax(4.5rem, 1fr))` }}>
          <div />
          {labels.map((l) => (
            <div key={l} className="px-1 pb-1 text-center text-xs font-medium text-muted-foreground">
              <span className="hidden sm:inline">Predicted </span>
              {label(l)}
            </div>
          ))}
          {labels.map((t, ti) => (
            <div key={t} className="contents">
              <div className="flex items-center pr-2 text-xs font-medium text-muted-foreground">
                <span className="hidden sm:inline">True&nbsp;</span>
                {label(t)}
              </div>
              {labels.map((p, pi) => {
                const count = matrix[ti][pi];
                const share = rowTotals[ti] ? count / rowTotals[ti] : 0;
                const correct = ti === pi;
                const isSelected = selected?.t === t && selected?.p === p;
                return (
                  <button
                    key={p}
                    type="button"
                    disabled={!onSelect || (count === 0)}
                    onMouseEnter={() => setHover({ t: ti, p: pi })}
                    onMouseLeave={() => setHover(null)}
                    onFocus={() => setHover({ t: ti, p: pi })}
                    onBlur={() => setHover(null)}
                    onClick={() => onSelect?.(t, p)}
                    aria-label={`${label(t)} predicted as ${label(p)}: ${count} sentences`}
                    className={cn(
                      "grid h-14 place-items-center rounded-md text-base font-semibold tabular-nums outline-none transition-transform focus-visible:ring-2 focus-visible:ring-ring enabled:hover:scale-[1.04]",
                      isSelected && "ring-2 ring-foreground",
                      count === 0 && "text-muted-foreground/50",
                    )}
                    style={{
                      background: count === 0
                        ? "var(--muted)"
                        : correct
                          ? `color-mix(in oklab, var(--primary) ${25 + share * 70}%, transparent)`
                          : `color-mix(in oklab, var(--destructive) ${30 + share * 60}%, transparent)`,
                    }}
                  >
                    {count}
                  </button>
                );
              })}
            </div>
          ))}
        </div>
      </div>
      <p className="min-h-5 text-sm text-muted-foreground" aria-live="polite">
        {hover && hovered
          ? hover.t === hover.p
            ? `${hovered.count} of ${hovered.total} "${label(labels[hover.t])}" sentences were recognised correctly (${hovered.total ? Math.round((hovered.count / hovered.total) * 100) : 0}%).`
            : `${hovered.count} "${label(labels[hover.t])}" sentence${hovered.count === 1 ? "" : "s"} were mistaken for "${label(labels[hover.p])}".`
          : "Green diagonal = correct. Red = a mistake. Hover a cell to read it" + (onSelect ? ", click a red cell to see those sentences." : ".")}
      </p>
    </div>
  );
}
