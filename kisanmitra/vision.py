"""Crop photo → disease prediction. Free, local, no API key, no PyTorch.

Model: MobileNetV2 fine-tuned on PlantVillage (38 classes), ONNX build from the
Hugging Face Hub (`onnx-community/mobilenet_v2_1.0_224-plant-disease-identification-ONNX`,
~9 MB, downloaded once and cached).

Reliability measures: predictions are averaged over 4 views of the photo (original and
mirrored, cropped and whole), and the farmer can say which crop it is, which restricts the
answer to that crop's classes. Even so:

Honest limits: PlantVillage photos are single leaves on plain backgrounds, and the
model only knows 14 crops. It is least reliable on busy field photos and on crops it
was never trained on (onion, wheat, cotton, rice, ...). Callers must treat low
confidence as "not sure" rather than as an answer.
"""

import io
import json
from dataclasses import dataclass
from functools import lru_cache

import numpy as np
from PIL import Image, ImageOps

# Words in a class label → crop id (the same ids as data/image_advice.json).
CROP_KEYWORDS = {
    "tomato": "tomato", "potato": "potato", "corn": "maize", "pepper": "capsicum", "grape": "grape",
    "apple": "apple", "cherry": "cherry", "peach": "peach", "strawberry": "strawberry", "squash": "squash",
    "orange": "citrus", "soybean": "soybean", "blueberry": "blueberry", "raspberry": "raspberry",
}

REPO = "onnx-community/mobilenet_v2_1.0_224-plant-disease-identification-ONNX"
MAX_BYTES = 12 * 1024 * 1024


@dataclass
class Prediction:
    index: int
    label: str
    confidence: float


@lru_cache(maxsize=1)
def _load():
    import onnxruntime as ort
    from huggingface_hub import hf_hub_download

    model_path = hf_hub_download(REPO, "onnx/model.onnx")
    config_path = hf_hub_download(REPO, "config.json")
    with open(config_path, encoding="utf-8") as f:
        labels = {int(k): v for k, v in json.load(f)["id2label"].items()}
    session = ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])
    return session, labels


def labels() -> dict[int, str]:
    return _load()[1]


def crop_of(label: str) -> str | None:
    low = label.lower()
    return next((crop for word, crop in CROP_KEYWORDS.items() if word in low), None)


def supported_crops() -> set[str]:
    """Crops with at least one DISEASE class. Crops with only a "Healthy" class (soybean, blueberry,
    raspberry) are excluded: the model could only ever answer "healthy" for them, which would mislead."""
    return {c for label in labels().values() if "healthy" not in label.lower() and (c := crop_of(label))}


def open_image(image_bytes: bytes) -> Image.Image:
    if len(image_bytes) > MAX_BYTES:
        raise ValueError("Image is too large (max 12 MB)")
    try:
        img = Image.open(io.BytesIO(image_bytes))
        return ImageOps.exif_transpose(img).convert("RGB")  # phone photos are often rotated via EXIF
    except Exception as exc:
        raise ValueError("That file is not a readable image") from exc


def to_tensor(img: Image.Image) -> np.ndarray:
    x = (np.asarray(img, dtype=np.float32) / 255.0 - 0.5) / 0.5  # scale to [-1, 1]
    return x.transpose(2, 0, 1)[None]  # NCHW


def center_crop_view(img: Image.Image) -> Image.Image:
    """The model's own preprocessing: short side → 256, then center-crop 224."""
    w, h = img.size
    scale = 256 / min(w, h)
    img = img.resize((max(224, round(w * scale)), max(224, round(h * scale))), Image.BILINEAR)
    w, h = img.size
    left, top = (w - 224) // 2, (h - 224) // 2
    return img.crop((left, top, left + 224, top + 224))


def preprocess(image_bytes: bytes) -> np.ndarray:
    return to_tensor(center_crop_view(open_image(image_bytes)))


def classify(image_bytes: bytes, top_k: int = 3, crop: str | None = None) -> list[Prediction]:
    """Predict the disease. `crop` (e.g. "tomato") limits the answer to that crop's classes."""
    session, names = _load()
    img = open_image(image_bytes)
    views = [center_crop_view(img), img.resize((224, 224), Image.BILINEAR)]  # cropped and whole photo
    views += [ImageOps.mirror(v) for v in views]

    probs = np.zeros(len(names))
    for view in views:
        logits = session.run(None, {session.get_inputs()[0].name: to_tensor(view)})[0][0]
        exp = np.exp(logits - logits.max())
        probs += exp / exp.sum()
    probs /= len(views)

    if crop:
        # Rank only this crop's classes, but do NOT re-normalize: if the model thought the photo
        # was another crop, the remaining probability stays low and the answer is reported as unsure.
        mask = np.array([crop_of(names[i]) == crop for i in range(len(names))])
        if mask.any():
            probs = np.where(mask, probs, 0.0)
    best = np.argsort(probs)[::-1][:top_k]
    return [Prediction(int(i), names[int(i)], round(float(probs[i]), 4)) for i in best]
