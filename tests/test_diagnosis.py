"""Photo diagnosis tests. The ONNX model itself is mocked; preprocessing is tested for real."""

import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from kisanmitra import diagnosis, server, vision
from kisanmitra.vision import Prediction

client = TestClient(server.app)


def jpeg(size=(640, 480), color=(40, 140, 40)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, "JPEG")
    return buf.getvalue()


def fake_classify(*preds):
    return lambda image_bytes, top_k=3, crop=None: [Prediction(i, label, conf) for i, (label, conf) in enumerate(preds)]


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setattr(diagnosis, "translate_ex", lambda text, target, **k: (text if target == "en" else f"[{target}] {text}", True))
    monkeypatch.setattr(vision, "labels", lambda: {
        0: "Healthy Soybean Plant", 1: "Tomato with Early Blight", 2: "Healthy Tomato Plant",
        3: "Potato with Late Blight", 4: "Healthy Blueberry Plant",
    })


def test_preprocess_shape_and_range():
    x = vision.preprocess(jpeg((1000, 300)))
    assert x.shape == (1, 3, 224, 224) and x.min() >= -1.0 and x.max() <= 1.0


def test_preprocess_rejects_non_image():
    with pytest.raises(ValueError, match="not a readable image"):
        vision.preprocess(b"this is not an image")


def test_confident_disease(monkeypatch):
    monkeypatch.setattr(vision, "classify", fake_classify(("Tomato with Late Blight", 0.97), ("Healthy Tomato Plant", 0.01)))
    r = diagnosis.diagnose(jpeg(), "en")
    assert r.intent == "crop_image" and r.entities["crop"] == "tomato"
    assert "Your plant has Late blight" in r.english and "Metalaxyl" in r.english
    assert r.details["vision"]["status"] == "confident"


def test_possible_uses_hedged_wording(monkeypatch):
    monkeypatch.setattr(vision, "classify", fake_classify(("Tomato with Early Blight", 0.40), ("Bell Pepper with Bacterial Spot", 0.33)))
    r = diagnosis.diagnose(jpeg(), "en")
    assert "may have Early blight" in r.english and r.details["vision"]["status"] == "possible"


def test_unsure_asks_for_better_photo(monkeypatch):
    monkeypatch.setattr(vision, "classify", fake_classify(("Tomato with Early Blight", 0.20)))
    r = diagnosis.diagnose(jpeg(), "en")
    assert r.details["vision"]["status"] == "unsure" and "close-up photo" in r.english
    assert r.entities["crop"] is None


def test_healthy_leaf(monkeypatch):
    monkeypatch.setattr(vision, "classify", fake_classify(("Healthy Potato Plant", 0.99)))
    r = diagnosis.diagnose(jpeg(), "en")
    assert "looks healthy" in r.english and r.details["vision"]["predictions"][0]["healthy"] is True


def test_label_without_advice_is_still_reported(monkeypatch):
    monkeypatch.setattr(vision, "classify", fake_classify(("Grape with Black Rot", 0.9)))
    assert "Grape with Black Rot" in diagnosis.diagnose(jpeg(), "en").english


def test_reply_is_translated(monkeypatch):
    monkeypatch.setattr(vision, "classify", fake_classify(("Healthy Tomato Plant", 0.99)))
    r = diagnosis.diagnose(jpeg(), "hi")
    assert r.text.startswith("[hi] ") and r.lang == "hi"


def test_endpoint(monkeypatch):
    monkeypatch.setattr(vision, "classify", fake_classify(("Potato with Early Blight", 0.95)))
    r = client.post("/api/diagnose", files={"image": ("leaf.jpg", jpeg(), "image/jpeg")}, data={"lang_pref": "auto"})
    body = r.json()
    assert r.status_code == 200 and body["lang"] == "en" and body["entities"]["crop"] == "potato"
    assert body["details"]["vision"]["predictions"][0]["label"] == "Potato with Early Blight"


def test_endpoint_rejects_bad_file():
    r = client.post("/api/diagnose", files={"image": ("x.jpg", b"nope", "image/jpeg")})
    assert r.status_code == 400


def test_endpoint_language_from_caption(monkeypatch):
    monkeypatch.setattr(vision, "classify", fake_classify(("Healthy Tomato Plant", 0.99)))
    r = client.post(
        "/api/diagnose",
        files={"image": ("leaf.jpg", jpeg(), "image/jpeg")},
        data={"lang_pref": "auto", "text": "नाशिक मध्ये कांद्याचा भाव काय आहे"},
    )
    assert r.json()["lang"] == "mr"


def test_supported_crops_excludes_healthy_only_crops():
    assert vision.supported_crops() == {"tomato", "potato"}  # soybean, blueberry only have a "Healthy" class


def test_wide_lead_is_required_for_confident(monkeypatch):
    monkeypatch.setattr(vision, "classify", fake_classify(("Tomato with Late Blight", 0.78), ("Tomato with Early Blight", 0.60)))
    r = diagnosis.diagnose(jpeg(), "en")
    assert r.details["vision"]["status"] == "possible" and "may have" in r.english


def test_crop_hint_is_passed_to_the_model(monkeypatch):
    seen = {}

    def spy(image_bytes, top_k=3, crop=None):
        seen["crop"] = crop
        return [Prediction(0, "Tomato with Late Blight", 0.95)]

    monkeypatch.setattr(vision, "classify", spy)
    diagnosis.diagnose(jpeg(), "en", crop="tomato")
    assert seen["crop"] == "tomato"
    diagnosis.diagnose(jpeg(), "en", text="mera tamatar ka patta")  # crop found in the caption
    assert seen["crop"] == "tomato"


def test_unsupported_crop_is_not_forced_into_a_wrong_class(monkeypatch):
    called = []
    monkeypatch.setattr(vision, "classify", lambda *a, **k: called.append(1))
    r = diagnosis.diagnose(jpeg(), "en", text="my onion leaves are drying")
    assert not called and r.details["vision"]["status"] == "unsupported"
    assert "cannot check onion" in r.english
    assert diagnosis.diagnose(jpeg(), "en", crop="soybean").details["vision"]["status"] == "unsupported"


def test_endpoint_passes_crop(monkeypatch):
    seen = {}
    monkeypatch.setattr(vision, "classify", lambda b, top_k=3, crop=None: seen.setdefault("crop", crop) and [Prediction(0, "Healthy Tomato Plant", 0.9)])
    client.post("/api/diagnose", files={"image": ("leaf.jpg", jpeg(), "image/jpeg")}, data={"crop": "tomato", "lang_pref": "en"})
    assert seen["crop"] == "tomato"
