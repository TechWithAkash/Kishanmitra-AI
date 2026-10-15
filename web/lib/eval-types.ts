export type PerClass = { label: string; precision: number; recall: number; f1: number; support: number };

export type ClassificationReport = {
  labels: string[];
  accuracy: number;
  kappa: number | null;
  macro: { precision: number; recall: number; f1: number };
  weighted: { precision: number; recall: number; f1: number };
  per_class: PerClass[];
  confusion: number[][]; // rows = true class, columns = predicted class
  n: number;
  by_language: { group: string; accuracy: number; n: number }[];
};

export type IntentError = { text: string; true: string; pred: string; confidence?: number; language: string };

export type IntentReport = ClassificationReport & {
  errors: IntentError[];
  mean_confidence_correct: number;
  mean_confidence_wrong: number | null;
  calibration: { range: string; n: number; accuracy: number | null; mean_confidence: number | null }[];
};

export type LangReport = ClassificationReport & { errors: IntentError[] };

export type ModelRow = {
  model: string;
  used_in_app: boolean;
  cv_macro_f1_mean: number;
  cv_macro_f1_std: number;
  test_accuracy: number;
  test_macro_f1: number;
};

export type EntityReport = {
  n: number;
  per_slot: { slot: string; precision: number; recall: number; f1: number; tp: number; fp: number; fn: number; support: number }[];
  micro: { precision: number; recall: number; f1: number };
  strict_accuracy: number;
  errors: { text: string; slot: string; gold: string | null; pred: string | null; kind: string }[];
};

export type EvaluationReport = {
  generated_at: string;
  dataset: {
    train_size: number;
    train_by_intent: Record<string, number>;
    train_by_language: Record<string, number>;
    test_size: number;
    test_size_intent: number;
    test_by_intent: Record<string, number>;
    test_by_language: Record<string, number>;
    overlap_with_training: number;
  };
  intent: IntentReport;
  models: ModelRow[];
  langid: LangReport;
  entities: EntityReport;
  latency: { samples: number; stages: { stage: string; median_ms: number; p95_ms: number; mean_ms: number }[] };
  limitations: string[];
};

export type Explanation = {
  text: string;
  language: { code: string; name: string; script: string };
  intent: { label: string; confidence: number; probabilities: Record<string, number> };
  entities: { type: string; value: string; text: string; start: number; end: number; how: string }[];
  milliseconds: number;
};

export type LiveSample = { id: string; text: string; predicted: string; actual: string; confidence: number; ts: number };
