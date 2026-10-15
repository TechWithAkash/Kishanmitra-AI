"""NLP performance measurement: the numbers and charts behind the "Model performance" page.

What is measured, on a TEST SET THAT THE MODELS NEVER SAW (data/eval/queries.csv; the training data is
data/intents.csv, and a check below proves the two share no sentence):

  * Language identification: accuracy, per-language accuracy, confusion matrix
  * Intent classification: accuracy, precision / recall / F1 per class, macro and weighted F1, Cohen's kappa,
    confusion matrix, per-language accuracy, confidence calibration, error list
  * Model comparison: 6 classifiers, each scored by 5-fold cross-validation on the training data (used to
    CHOOSE a model) and on the test set (used to REPORT it): choosing on the test set would be cheating
  * Entity extraction (crop, symptom, place): precision / recall / F1 per type, strict slot-filling accuracy
  * Speed: median and 95th-percentile latency of each stage

Run as a script to print the report and write docs/evaluation_report.md:  uv run python -m kisanmitra.evaluation
"""

import csv
import statistics
import threading
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone

import numpy as np
from sklearn.dummy import DummyClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, cohen_kappa_score, confusion_matrix, precision_recall_fscore_support
from sklearn.model_selection import StratifiedKFold
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import FeatureUnion, make_pipeline
from sklearn.svm import LinearSVC

from kisanmitra import DATA_DIR, LANG_NAMES, intent as intent_module
from kisanmitra.entities import explain_entities, extract_entities
from kisanmitra.langid import detect_language

EVAL_FILE = DATA_DIR / "eval" / "queries.csv"
SLOTS = ("crop", "symptom", "location")
CACHE_SECONDS = 600

LIMITATIONS = [
    "The test set was written by the project developer (134 sentences), not collected from real farmers. It is small, so differences of a few percent are not meaningful. A real evaluation needs queries from farmers.",
    "Intent classification covers 4 intents (crop problem, price, weather, general) and was trained on only about 140 sentences, in Hindi, Marathi and English. Other languages are translated to English first and are not scored here.",
    "Entity extraction uses keyword lists (8 crops, about 40 cities, 6 symptom groups) plus spelling correction. It scores well on words it knows and finds nothing for words it does not.",
    "Not yet measured: speech recognition accuracy (WER), translation quality (BLEU/chrF), and the AI photo check. Weather and mandi answers come from external services, so their correctness is not an NLP measure.",
]


# ---------------------------------------------------------------- data

def load_queries() -> list[dict]:
    with open(EVAL_FILE, encoding="utf-8") as f:
        return [{**r, "use_for_intent": r["use_for_intent"] == "1"} for r in csv.DictReader(f)]


def _lang_label(lang: str, script: str) -> str:
    return f"{lang}-roman" if script == "latin" and lang != "en" else lang


def _name(label: str) -> str:
    base = label.replace("-roman", "")
    return f"{LANG_NAMES.get(base, base)}{' (romanized)' if label.endswith('-roman') else ''}"


def dataset_summary(queries: list[dict]) -> dict:
    texts, labels, langs = intent_module.load_dataset()
    train = {t.strip().lower() for t in texts}
    test = {q["text"].strip().lower() for q in queries}
    return {
        "train_size": len(texts),
        "train_by_intent": dict(Counter(labels)),
        "train_by_language": dict(Counter(langs)),
        "test_size": len(queries),
        "test_size_intent": sum(q["use_for_intent"] for q in queries),
        "test_by_intent": dict(Counter(q["intent"] for q in queries if q["use_for_intent"])),
        "test_by_language": dict(Counter(_name(_lang_label(q["lang"], q["script"])) for q in queries)),
        "overlap_with_training": len(train & test),   # must be 0
    }


# ---------------------------------------------------------------- metrics helpers

def _classification(y_true: list[str], y_pred: list[str], labels: list[str]) -> dict:
    p, r, f, support = precision_recall_fscore_support(y_true, y_pred, labels=labels, zero_division=0)
    wp, wr, wf, _ = precision_recall_fscore_support(y_true, y_pred, labels=labels, average="weighted", zero_division=0)
    mp, mr, mf, _ = precision_recall_fscore_support(y_true, y_pred, labels=labels, average="macro", zero_division=0)
    return {
        "labels": labels,
        "accuracy": round(accuracy_score(y_true, y_pred), 4),
        "kappa": round(float(cohen_kappa_score(y_true, y_pred, labels=labels)), 4) if len(set(y_true)) > 1 else None,
        "macro": {"precision": round(mp, 4), "recall": round(mr, 4), "f1": round(mf, 4)},
        "weighted": {"precision": round(wp, 4), "recall": round(wr, 4), "f1": round(wf, 4)},
        "per_class": [
            {"label": lab, "precision": round(float(p[i]), 4), "recall": round(float(r[i]), 4), "f1": round(float(f[i]), 4), "support": int(support[i])}
            for i, lab in enumerate(labels)
        ],
        "confusion": confusion_matrix(y_true, y_pred, labels=labels).tolist(),   # rows = true, columns = predicted
    }


def _accuracy_by(rows: list[dict], key: str) -> list[dict]:
    groups: dict[str, list[bool]] = defaultdict(list)
    for r in rows:
        groups[r[key]].append(r["correct"])
    return [{"group": g, "accuracy": round(sum(v) / len(v), 4), "n": len(v)} for g, v in sorted(groups.items())]


# ---------------------------------------------------------------- intent + model comparison

def candidate_models() -> dict:
    char = lambda: TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), sublinear_tf=True)
    word = lambda: TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True)
    return {
        "Majority class (baseline)": make_pipeline(DummyClassifier(strategy="most_frequent")),
        "Word TF-IDF + Logistic Regression": make_pipeline(word(), LogisticRegression(C=10, max_iter=2000, class_weight="balanced")),
        "Character TF-IDF + Logistic Regression (used in the app)": intent_module.build_model(),
        "Character TF-IDF + Linear SVM": make_pipeline(char(), LinearSVC(class_weight="balanced")),
        "Character TF-IDF + Naive Bayes": make_pipeline(char(), MultinomialNB()),
        "Character + Word TF-IDF + Logistic Regression": make_pipeline(
            FeatureUnion([("char", char()), ("word", word())]), LogisticRegression(C=10, max_iter=2000, class_weight="balanced")),
    }


def evaluate_intent(queries: list[dict]) -> dict:
    texts, labels, _ = intent_module.load_dataset()
    classes = list(intent_module.INTENTS)
    test = [q for q in queries if q["use_for_intent"]]
    x_test = [q["text"].lower() for q in test]
    y_test = [q["intent"] for q in test]

    app_model = intent_module.build_model().fit(texts, labels)       # the same model the app uses
    probs = app_model.predict_proba(x_test)
    pred = [str(app_model.classes_[i]) for i in probs.argmax(axis=1)]
    conf = probs.max(axis=1)

    rows = [{"text": q["text"], "true": t, "pred": p, "confidence": round(float(c), 3), "correct": t == p,
             "language": _name(_lang_label(q["lang"], q["script"]))} for q, t, p, c in zip(test, y_test, pred, conf)]
    result = _classification(y_test, pred, classes)
    result["n"] = len(rows)
    result["by_language"] = _accuracy_by(rows, "language")
    result["errors"] = [r for r in rows if not r["correct"]]
    result["mean_confidence_correct"] = round(float(np.mean([r["confidence"] for r in rows if r["correct"]])), 3)
    wrong = [r["confidence"] for r in rows if not r["correct"]]
    result["mean_confidence_wrong"] = round(float(np.mean(wrong)), 3) if wrong else None

    # Calibration: when the model says "70% sure", is it right about 70% of the time?
    bins = [(0.0, 0.5), (0.5, 0.7), (0.7, 0.85), (0.85, 1.01)]
    result["calibration"] = [
        {"range": f"{int(lo * 100)}-{min(int(hi * 100), 100)}%", "n": len(sel), "accuracy": round(sum(r["correct"] for r in sel) / len(sel), 4) if sel else None,
         "mean_confidence": round(float(np.mean([r["confidence"] for r in sel])), 3) if sel else None}
        for lo, hi in bins for sel in [[r for r in rows if lo <= r["confidence"] < hi]]
    ]
    return result


def evaluate_models(queries: list[dict]) -> list[dict]:
    texts, labels, _ = intent_module.load_dataset()
    texts_a, labels_a = np.array(texts, dtype=object), np.array(labels)
    test = [q for q in queries if q["use_for_intent"]]
    x_test, y_test = [q["text"].lower() for q in test], [q["intent"] for q in test]
    folds = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    out = []
    for name, model in candidate_models().items():
        scores = []
        for train_idx, val_idx in folds.split(texts_a, labels_a):
            fold = _fresh(name).fit(list(texts_a[train_idx]), list(labels_a[train_idx]))
            scores.append(precision_recall_fscore_support(labels_a[val_idx], fold.predict(list(texts_a[val_idx])), average="macro", zero_division=0)[2])
        fitted = model.fit(texts, labels)
        pred = fitted.predict(x_test)
        out.append({
            "model": name,
            "used_in_app": "used in the app" in name,
            "cv_macro_f1_mean": round(float(np.mean(scores)), 4),
            "cv_macro_f1_std": round(float(np.std(scores)), 4),
            "test_accuracy": round(accuracy_score(y_test, pred), 4),
            "test_macro_f1": round(float(precision_recall_fscore_support(y_test, pred, average="macro", zero_division=0)[2]), 4),
        })
    return out


def _fresh(name: str):
    return candidate_models()[name]


# ---------------------------------------------------------------- language identification

def evaluate_langid(queries: list[dict]) -> dict:
    rows = []
    for q in queries:
        got = detect_language(q["text"])
        true_label, pred_label = _lang_label(q["lang"], q["script"]), _lang_label(got.lang, got.script)
        rows.append({"text": q["text"], "true": _name(true_label), "pred": _name(pred_label), "correct": true_label == pred_label,
                     "language": _name(true_label)})
    labels = sorted({r["true"] for r in rows} | {r["pred"] for r in rows})
    result = _classification([r["true"] for r in rows], [r["pred"] for r in rows], labels)
    result["n"] = len(rows)
    result["by_language"] = _accuracy_by(rows, "language")
    result["errors"] = [r for r in rows if not r["correct"]]
    return result


# ---------------------------------------------------------------- entities

def evaluate_entities(queries: list[dict]) -> dict:
    test = [q for q in queries if q["use_for_intent"]]
    counts = {s: {"tp": 0, "fp": 0, "fn": 0} for s in SLOTS}
    errors, strict_ok = [], 0
    for q in test:
        pred = extract_entities(q["text"])
        ok_row = True
        for slot in SLOTS:
            gold, got = q[slot] or None, getattr(pred, slot)
            c = counts[slot]
            if gold and got == gold:
                c["tp"] += 1
            elif gold and got and got != gold:
                c["fp"] += 1; c["fn"] += 1; ok_row = False
                errors.append({"text": q["text"], "slot": slot, "gold": gold, "pred": got, "kind": "wrong value"})
            elif gold and not got:
                c["fn"] += 1; ok_row = False
                errors.append({"text": q["text"], "slot": slot, "gold": gold, "pred": None, "kind": "missed"})
            elif got and not gold:
                c["fp"] += 1; ok_row = False
                errors.append({"text": q["text"], "slot": slot, "gold": None, "pred": got, "kind": "extra"})
        strict_ok += ok_row

    def prf(tp, fp, fn):
        p = tp / (tp + fp) if tp + fp else 0.0
        r = tp / (tp + fn) if tp + fn else 0.0
        return round(p, 4), round(r, 4), round(2 * p * r / (p + r), 4) if p + r else 0.0

    per_slot = []
    for slot in SLOTS:
        c = counts[slot]
        p, r, f = prf(c["tp"], c["fp"], c["fn"])
        per_slot.append({"slot": slot, "precision": p, "recall": r, "f1": f, **c, "support": c["tp"] + c["fn"]})
    total = {k: sum(counts[s][k] for s in SLOTS) for k in ("tp", "fp", "fn")}
    p, r, f = prf(**total)
    return {"n": len(test), "per_slot": per_slot, "micro": {"precision": p, "recall": r, "f1": f},
            "strict_accuracy": round(strict_ok / len(test), 4), "errors": errors}


# ---------------------------------------------------------------- speed

def _percentile(values: list[float], q: float) -> float:
    return float(np.percentile(values, q))


def evaluate_latency(queries: list[dict], repeats: int = 5) -> dict:
    texts = [q["text"] for q in queries]
    for t in texts[:5]:   # warm up (first calls load models / compile regexes)
        detect_language(t); intent_module.predict_intent(t); extract_entities(t)
    stages: dict[str, list[float]] = {"Language ID": [], "Intent": [], "Entities": [], "Total": []}
    for _ in range(repeats):
        for t in texts:
            a = time.perf_counter(); detect_language(t)
            b = time.perf_counter(); intent_module.predict_intent(t)
            c = time.perf_counter(); extract_entities(t)
            d = time.perf_counter()
            stages["Language ID"].append((b - a) * 1000); stages["Intent"].append((c - b) * 1000)
            stages["Entities"].append((d - c) * 1000); stages["Total"].append((d - a) * 1000)
    return {"samples": len(stages["Total"]), "stages": [
        {"stage": s, "median_ms": round(statistics.median(v), 2), "p95_ms": round(_percentile(v, 95), 2), "mean_ms": round(statistics.fmean(v), 2)}
        for s, v in stages.items()]}


# ---------------------------------------------------------------- live explanation

def explain(text: str) -> dict:
    """Everything the pipeline understands about one sentence: for the interactive demo."""
    started = time.perf_counter()
    lang = detect_language(text)
    probs = intent_module.intent_probabilities(text)
    best = max(probs, key=probs.get)
    return {
        "text": text,
        "language": {"code": lang.lang, "name": _name(_lang_label(lang.lang, lang.script)), "script": lang.script},
        "intent": {"label": best, "confidence": probs[best], "probabilities": probs},
        "entities": explain_entities(text),
        "milliseconds": round((time.perf_counter() - started) * 1000, 2),
    }


# ---------------------------------------------------------------- everything

_cache: tuple[float, dict] | None = None
_lock = threading.Lock()


def build_report() -> dict:
    queries = load_queries()
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "dataset": dataset_summary(queries),
        "intent": evaluate_intent(queries),
        "models": evaluate_models(queries),
        "langid": evaluate_langid(queries),
        "entities": evaluate_entities(queries),
        "latency": evaluate_latency(queries),
        "limitations": LIMITATIONS,
    }


def get_report(refresh: bool = False) -> dict:
    global _cache
    with _lock:
        if not refresh and _cache and time.monotonic() - _cache[0] < CACHE_SECONDS:
            return _cache[1]
        report = build_report()
        _cache = (time.monotonic(), report)
        return report


# ---------------------------------------------------------------- written report

def to_markdown(r: dict) -> str:
    d, i, l, e = r["dataset"], r["intent"], r["langid"], r["entities"]
    pct = lambda v: f"{v * 100:.1f}%"
    out = [
        "# KisanMitra AI: NLP performance report", "",
        f"Generated {r['generated_at']} by `uv run python -m kisanmitra.evaluation`.", "",
        "## Data", "",
        f"- Training sentences: **{d['train_size']}** ({', '.join(f'{k}: {v}' for k, v in d['train_by_intent'].items())})",
        f"- Test sentences (never seen in training): **{d['test_size']}** ({d['test_size_intent']} used for intent). Overlap with training: **{d['overlap_with_training']}**",
        f"- Test languages: {', '.join(f'{k}: {v}' for k, v in d['test_by_language'].items())}", "",
        "## Intent classification (Character TF-IDF + Logistic Regression)", "",
        f"Accuracy **{pct(i['accuracy'])}**, macro precision {pct(i['macro']['precision'])}, macro recall {pct(i['macro']['recall'])}, "
        f"**macro F1 {pct(i['macro']['f1'])}**, weighted F1 {pct(i['weighted']['f1'])}, Cohen's kappa {i['kappa']}.", "",
        "| Intent | Precision | Recall | F1 | Support |", "|---|---|---|---|---|",
        *[f"| {c['label']} | {pct(c['precision'])} | {pct(c['recall'])} | {pct(c['f1'])} | {c['support']} |" for c in i["per_class"]], "",
        "Confusion matrix (rows = true, columns = predicted):", "",
        "| true \\ predicted | " + " | ".join(i["labels"]) + " |", "|---|" + "---|" * len(i["labels"]),
        *[f"| {lab} | " + " | ".join(str(v) for v in row) + " |" for lab, row in zip(i["labels"], i["confusion"])], "",
        "## Model comparison", "",
        "| Model | CV macro-F1 (5-fold, training data) | Test accuracy | Test macro-F1 |", "|---|---|---|---|",
        *[f"| {m['model']} | {pct(m['cv_macro_f1_mean'])} ± {pct(m['cv_macro_f1_std'])} | {pct(m['test_accuracy'])} | {pct(m['test_macro_f1'])} |" for m in r["models"]], "",
        "## Language identification", "",
        f"Accuracy **{pct(l['accuracy'])}** on {l['n']} sentences. Per language: " + ", ".join(f"{g['group']} {pct(g['accuracy'])} (n={g['n']})" for g in l["by_language"]) + ".", "",
        "## Entity extraction", "",
        "| Entity | Precision | Recall | F1 | Support |", "|---|---|---|---|---|",
        *[f"| {s['slot']} | {pct(s['precision'])} | {pct(s['recall'])} | {pct(s['f1'])} | {s['support']} |" for s in e["per_slot"]],
        f"| **overall (micro)** | {pct(e['micro']['precision'])} | {pct(e['micro']['recall'])} | {pct(e['micro']['f1'])} | |", "",
        f"Strict slot-filling accuracy (every entity of a sentence exactly right): **{pct(e['strict_accuracy'])}**.", "",
        "## Speed (one sentence, one CPU thread)", "",
        "| Stage | Median | 95th percentile |", "|---|---|---|",
        *[f"| {s['stage']} | {s['median_ms']} ms | {s['p95_ms']} ms |" for s in r["latency"]["stages"]], "",
        "## Limitations", "", *[f"- {t}" for t in r["limitations"]], "",
    ]
    return "\n".join(out)


if __name__ == "__main__":
    report = build_report()
    text = to_markdown(report)
    path = DATA_DIR.parent / "docs" / "evaluation_report.md"
    path.parent.mkdir(exist_ok=True)
    path.write_text(text, encoding="utf-8")
    print(text)
    print(f"\n(written to {path})")
