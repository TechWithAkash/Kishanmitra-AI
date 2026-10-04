"""Step 2 — intent classification: TF-IDF character n-grams + Logistic Regression.

Character n-grams work across Devanagari and Latin script and are robust to the
spelling variation of romanized Hindi (pyaj / pyaz / pyaaz).

Run `uv run python -m kisanmitra.intent` to print held-out accuracy.
"""

import csv
from functools import lru_cache

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline, make_pipeline

from kisanmitra import DATA_DIR

INTENTS = ("crop_disease", "market_price", "weather", "general")


def load_dataset() -> tuple[list[str], list[str], list[str]]:
    texts, labels, langs = [], [], []
    with open(DATA_DIR / "intents.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            texts.append(row["text"].lower())
            labels.append(row["intent"])
            langs.append(row["lang"])
    return texts, labels, langs


def build_model() -> Pipeline:
    return make_pipeline(
        TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), sublinear_tf=True),
        LogisticRegression(C=10, max_iter=2000, class_weight="balanced"),
    )


@lru_cache(maxsize=1)
def get_model() -> Pipeline:
    texts, labels, _ = load_dataset()
    return build_model().fit(texts, labels)


def predict_intent(text: str) -> tuple[str, float]:
    model = get_model()
    probs = model.predict_proba([text.lower()])[0]
    best = probs.argmax()
    return str(model.classes_[best]), float(probs[best])


def evaluate() -> None:
    from sklearn.metrics import classification_report
    from sklearn.model_selection import train_test_split

    texts, labels, langs = load_dataset()
    x_tr, x_te, y_tr, y_te, _, l_te = train_test_split(
        texts, labels, langs, test_size=0.25, stratify=labels, random_state=42
    )
    model = build_model().fit(x_tr, y_tr)
    pred = model.predict(x_te)
    print(f"Train: {len(x_tr)}  Test: {len(x_te)}\n")
    print(classification_report(y_te, pred, digits=3))
    print("Accuracy by language:")
    for lang in sorted(set(l_te)):
        idx = [i for i, l in enumerate(l_te) if l == lang]
        acc = sum(pred[i] == y_te[i] for i in idx) / len(idx)
        print(f"  {lang:9s} {acc:.3f}  (n={len(idx)})")


if __name__ == "__main__":
    evaluate()
