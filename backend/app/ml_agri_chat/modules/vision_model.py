from __future__ import annotations

import json
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

try:
    import numpy as np
    from PIL import Image
except ImportError:  # pragma: no cover - exercised when optional image deps are absent locally.
    np = None
    Image = None


@dataclass
class VisionPrediction:
    disease_label: str
    confidence: float
    observed_symptoms: list[str]


class CoffeeVisionClassifier:
    """Loads a real Keras model when available; otherwise uses deterministic placeholder logic."""

    def __init__(self, model_path: str | Path | None = None):
        self.model_path = Path(model_path) if model_path else None
        self.model = None
        self.model_error: str | None = None
        self.label_map = {
            0: "gi_sat_la_ca_phe",
            1: "dom_mat_cua",
            2: "than_thu",
            3: "cay_khoe",
        }
        self._load_label_map()

    def predict(self, image_bytes: bytes) -> VisionPrediction:
        if self.model_path and self.model_path.exists():
            prediction = self._model_predict(image_bytes)
            if prediction:
                return prediction
        return self._placeholder_predict(image_bytes)

    def _load_label_map(self) -> None:
        if not self.model_path:
            return
        label_map_path = self.model_path.parent / "label_map.json"
        if not label_map_path.exists():
            return
        try:
            payload = json.loads(label_map_path.read_text(encoding="utf-8"))
            self.label_map = {int(index): label for index, label in payload.items()}
        except Exception as exc:
            self.model_error = f"Could not load label_map.json: {exc}"

    def _model_predict(self, image_bytes: bytes) -> VisionPrediction | None:
        if np is None or Image is None:
            self.model_error = "Image dependencies unavailable, using placeholder fallback."
            return None
        try:
            import tensorflow as tf  # type: ignore

            if self.model is None:
                self.model = tf.keras.models.load_model(self.model_path)
            image = Image.open(BytesIO(image_bytes)).convert("RGB").resize((224, 224))
            arr = np.array(image).astype(np.float32)
            batch = np.expand_dims(arr, axis=0)
            try:
                batch = tf.keras.applications.mobilenet_v2.preprocess_input(batch)
            except Exception:
                batch = batch / 255.0
            probabilities = self.model.predict(batch, verbose=0)[0]
            index = int(np.argmax(probabilities))
            label = self.label_map.get(index, str(index))
            confidence = float(probabilities[index])
            return VisionPrediction(label, round(confidence, 2), _symptoms(label, 0, 0, 0, 0))
        except Exception as exc:
            self.model_error = f"Real model unavailable, using placeholder: {exc}"
            return None

    def _placeholder_predict(self, image_bytes: bytes) -> VisionPrediction:
        if np is None or Image is None:
            return VisionPrediction(
                "unknown",
                0.0,
                ["thiếu thư viện xử lý ảnh trong môi trường backend hiện tại"],
            )
        image = Image.open(BytesIO(image_bytes)).convert("RGB").resize((224, 224))
        arr = np.array(image).astype(np.float32)
        red = arr[:, :, 0]
        green = arr[:, :, 1]
        blue = arr[:, :, 2]

        rust = ((red > 120) & (green > 65) & (green < 155) & (blue < 100)).mean()
        dark_spots = ((red < 95) & (green < 95) & (blue < 85)).mean()
        yellowing = ((red > 130) & (green > 115) & (blue < 95)).mean()
        healthy_green = ((green > red + 15) & (green > blue + 15) & (green > 70)).mean()

        scores = {
            "gi_sat_la_ca_phe": 0.42 + rust * 2.2 + yellowing * 0.35,
            "dom_mat_cua": 0.38 + dark_spots * 1.8 + yellowing * 0.55,
            "than_thu": 0.36 + dark_spots * 1.3 + (1 - healthy_green) * 0.22,
            "cay_khoe": 0.36 + healthy_green * 0.9 - rust * 0.25 - dark_spots * 0.35,
        }
        label = max(scores, key=scores.get)
        confidence = max(0.35, min(0.96, scores[label]))
        symptoms = _symptoms(label, rust, dark_spots, yellowing, healthy_green)
        return VisionPrediction(label, round(float(confidence), 2), symptoms)


def _symptoms(label: str, rust: float, dark_spots: float, yellowing: float, healthy_green: float) -> list[str]:
    base = {
        "gi_sat_la_ca_phe": ["vùng vàng nâu/cam giống gỉ sắt", "có thể có quầng vàng trên lá"],
        "dom_mat_cua": ["đốm nâu hoặc đen nhỏ", "có thể có vùng vàng quanh đốm"],
        "than_thu": ["mảng hoại tử sẫm màu", "có thể cháy mép lá hoặc vết bệnh lan rộng"],
        "cay_khoe": ["mô lá xanh là chủ yếu", "chưa thấy mẫu bệnh rõ"],
    }[label]
    extra = []
    if rust > 0.04:
        extra.append("nhiều điểm màu nâu/cam")
    if dark_spots > 0.08:
        extra.append("tỷ lệ vùng tối cao")
    if yellowing > 0.1:
        extra.append("có vàng lá")
    if healthy_green > 0.4:
        extra.append("vùng xanh của cây chiếm đáng kể")
    return base + extra
