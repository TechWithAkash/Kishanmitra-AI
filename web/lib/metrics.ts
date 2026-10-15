import type { LiveSample, PerClass } from "./eval-types";

/** Precision, recall and F1 computed from a list of (actual, predicted) pairs. Same formulas as scikit-learn. */
export function classMetrics(samples: LiveSample[], labels: string[]) {
  const perClass: PerClass[] = labels.map((label) => {
    const tp = samples.filter((s) => s.actual === label && s.predicted === label).length;
    const fp = samples.filter((s) => s.actual !== label && s.predicted === label).length;
    const fn = samples.filter((s) => s.actual === label && s.predicted !== label).length;
    const precision = tp + fp ? tp / (tp + fp) : 0;
    const recall = tp + fn ? tp / (tp + fn) : 0;
    return { label, precision, recall, f1: precision + recall ? (2 * precision * recall) / (precision + recall) : 0, support: tp + fn };
  });
  const present = perClass.filter((c) => c.support > 0);
  const macroF1 = present.length ? present.reduce((a, c) => a + c.f1, 0) / present.length : 0;
  const accuracy = samples.length ? samples.filter((s) => s.actual === s.predicted).length / samples.length : 0;
  const confusion = labels.map((t) => labels.map((p) => samples.filter((s) => s.actual === t && s.predicted === p).length));
  return { perClass, macroF1, accuracy, confusion };
}

export const pct = (v: number, digits = 1) => `${(v * 100).toFixed(digits)}%`;

export function toCsv(samples: LiveSample[]): string {
  const esc = (v: string | number) => `"${String(v).replace(/"/g, '""')}"`;
  const rows = samples.map((s) => [s.text, s.actual, s.predicted, s.predicted === s.actual ? "correct" : "wrong", s.confidence].map(esc).join(","));
  return ["text,actual_intent,predicted_intent,result,confidence", ...rows].join("\n");
}
