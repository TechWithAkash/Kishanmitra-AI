"""The performance numbers shown to the examiner must be right: check the formulas against hand calculations."""

import pytest
from fastapi.testclient import TestClient

from kisanmitra import evaluation as ev
from kisanmitra import server
from kisanmitra.entities import Entities
from kisanmitra.guards import RateLimiter

client = TestClient(server.app)


def test_precision_recall_f1_match_a_hand_calculation():
    # true: a a b b | predicted: a b b b
    #   class a: precision 1/1, recall 1/2, F1 = 2*1*.5/1.5 = 0.6667
    #   class b: precision 2/3, recall 2/2, F1 = 2*(2/3)*1/(5/3) = 0.8
    r = ev._classification(["a", "a", "b", "b"], ["a", "b", "b", "b"], ["a", "b"])
    a, b = r["per_class"]
    assert (a["precision"], a["recall"], a["f1"], a["support"]) == (1.0, 0.5, 0.6667, 2)
    assert (b["precision"], b["recall"], b["f1"], b["support"]) == (0.6667, 1.0, 0.8, 2)
    assert r["accuracy"] == 0.75 and r["macro"]["f1"] == 0.7333
    assert r["confusion"] == [[1, 1], [0, 2]]          # rows = true class, columns = predicted class


def test_a_perfect_classifier_scores_one_everywhere():
    r = ev._classification(["a", "b", "a"], ["a", "b", "a"], ["a", "b"])
    assert r["accuracy"] == 1.0 and r["macro"]["f1"] == 1.0 and r["kappa"] == 1.0


def test_entity_precision_recall_count_wrong_missed_and_extra_values(monkeypatch):
    queries = [
        {"text": "q1", "crop": "tomato", "symptom": "", "location": "", "use_for_intent": True},     # right
        {"text": "q2", "crop": "onion", "symptom": "", "location": "", "use_for_intent": True},      # wrong value
        {"text": "q3", "crop": "potato", "symptom": "", "location": "", "use_for_intent": True},     # missed
        {"text": "q4", "crop": "", "symptom": "", "location": "", "use_for_intent": True},           # extra
    ]
    answers = {"q1": Entities(crop="tomato"), "q2": Entities(crop="wheat"), "q3": Entities(), "q4": Entities(crop="cotton")}
    monkeypatch.setattr(ev, "extract_entities", lambda text: answers[text])
    crop = next(s for s in ev.evaluate_entities(queries)["per_slot"] if s["slot"] == "crop")
    # TP=1 (q1) | FP=2 (q2 wrong value, q4 extra) | FN=2 (q2 wrong value, q3 missed)
    assert (crop["tp"], crop["fp"], crop["fn"]) == (1, 2, 2)
    assert crop["precision"] == crop["recall"] == 0.3333 and crop["f1"] == 0.3333
    out = ev.evaluate_entities(queries)
    assert out["strict_accuracy"] == 0.25 and {e["kind"] for e in out["errors"]} == {"wrong value", "missed", "extra"}


def test_the_test_set_shares_no_sentence_with_the_training_data():
    summary = ev.dataset_summary(ev.load_queries())
    assert summary["overlap_with_training"] == 0
    assert summary["test_size"] >= 100 and summary["train_size"] >= 100


def test_every_intent_is_present_in_the_test_set():
    by_intent = ev.dataset_summary(ev.load_queries())["test_by_intent"]
    assert set(by_intent) == {"crop_disease", "market_price", "weather", "general"} and min(by_intent.values()) >= 10


def test_language_identification_is_scored_per_language():
    result = ev.evaluate_langid(ev.load_queries())
    assert 0.9 <= result["accuracy"] <= 1.0
    assert {g["group"] for g in result["by_language"]} >= {"English", "Hindi", "Marathi", "Hindi (romanized)", "Tamil"}
    assert all(row["pred"] != row["true"] for row in result["errors"])


def test_the_comparison_includes_a_baseline_and_picks_by_cross_validation_not_by_the_test_set():
    models = ev.evaluate_models(ev.load_queries())
    by_name = {m["model"]: m for m in models}
    baseline = by_name["Majority class (baseline)"]
    app = next(m for m in models if m["used_in_app"])
    assert len(models) == 6 and baseline["test_macro_f1"] < 0.3 and app["test_macro_f1"] > baseline["test_macro_f1"] + 0.5
    assert all(0 <= m["cv_macro_f1_mean"] <= 1 and m["cv_macro_f1_std"] >= 0 for m in models)


def test_intent_report_has_everything_the_page_draws():
    r = ev.evaluate_intent(ev.load_queries())
    assert r["labels"] == ["crop_disease", "market_price", "weather", "general"]
    assert len(r["confusion"]) == 4 and sum(map(sum, r["confusion"])) == r["n"]
    assert abs(sum(c["recall"] * c["support"] for c in r["per_class"]) / r["n"] - r["accuracy"]) < 0.01   # weighted recall == accuracy
    assert r["calibration"] and all("range" in c for c in r["calibration"])
    assert all(not e["correct"] for e in r["errors"]) and len(r["errors"]) == round(r["n"] * (1 - r["accuracy"]))


def test_latency_is_measured_per_stage():
    stages = {s["stage"]: s for s in ev.evaluate_latency(ev.load_queries()[:20], repeats=2)["stages"]}
    assert set(stages) == {"Language ID", "Intent", "Entities", "Total"}
    assert all(0 < s["median_ms"] <= s["p95_ms"] for s in stages.values())


def test_live_explanation_gives_language_probabilities_and_highlighted_entities():
    e = ev.explain("mera tamatar peela ho raha hai in Pune")
    assert e["language"]["code"] == "hi" and e["language"]["script"] == "latin"
    assert e["intent"]["label"] == "crop_disease" and abs(sum(e["intent"]["probabilities"].values()) - 1) < 0.01
    found = {x["type"]: x for x in e["entities"]}
    assert found["crop"]["value"] == "tomato" and e["text"][found["crop"]["start"]:found["crop"]["end"]] == "tamatar"
    assert found["location"]["value"] == "Pune" and found["symptom"]["value"] == "yellowing"


def test_spelling_corrected_entities_are_labelled_as_such():
    e = ev.explain("my tomatoo leaves look yello")
    assert {x["type"]: x["how"] for x in e["entities"]} == {"crop": "spelling correction", "symptom": "spelling correction"}


def test_written_report_contains_the_headline_numbers():
    md = ev.to_markdown(ev.build_report())
    for heading in ("## Intent classification", "## Model comparison", "## Language identification", "## Entity extraction", "## Limitations"):
        assert heading in md
    assert "Overlap with training: **0**" in md and "Confusion matrix" in md


def test_evaluation_endpoints(monkeypatch):
    monkeypatch.setattr(server, "normal_limiter", RateLimiter(10_000))
    body = client.get("/api/evaluation").json()
    assert {"dataset", "intent", "models", "langid", "entities", "latency", "limitations"} <= set(body)
    assert body["dataset"]["overlap_with_training"] == 0
    exp = client.post("/api/evaluation/explain", json={"text": "onion price in Nashik"}).json()
    assert exp["intent"]["label"] == "market_price" and exp["language"]["code"] == "en"
    assert client.post("/api/evaluation/explain", json={"text": ""}).status_code == 422
    assert client.post("/api/evaluation/explain", json={"text": "x" * 1000}).status_code == 422
