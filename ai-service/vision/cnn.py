"""CNN académica (PyTorch) — 8 clases visuales, NUNCA fake/real.

Arquitectura (equivalente Keras):

    Input 64×64 RGB
      → Conv2D 32, 3×3, ReLU → MaxPool 2×2
      → Conv2D 64, 3×3, ReLU → MaxPool 2×2
      → Conv2D 64, 3×3, ReLU
      → Flatten
      → Dense 64, ReLU
      → Dense 8  (logits; softmax en inferencia)

compile: Adam + sparse_categorical_crossentropy + accuracy
Pesos: models/cnn/vision_cnn_v1.pt
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_FW = Path(__file__).resolve().parents[2]
if str(_FW) not in sys.path:
    sys.path.insert(0, str(_FW))
from bootstrap import CNN_WEIGHTS, ensure_paths  # noqa: E402

ensure_paths()

# Orden académico pedido (índice = etiqueta sparse)
IMAGE_CLASSES = (
    "OFFICIAL_DOCUMENT",       # 0
    "NEWS_SCREENSHOT",         # 1
    "SOCIAL_MEDIA",            # 2
    "MEME",                    # 3
    "INFOGRAPHIC",             # 4
    "ANIMAL_HEALTH_CONTENT",   # 5
    "PHOTOGRAPH",              # 6
    "POTENTIALLY_MANIPULATED", # 7
)

CLASS_LABELS_ES = {
    "OFFICIAL_DOCUMENT": "Documento oficial",
    "NEWS_SCREENSHOT": "Noticia / captura",
    "SOCIAL_MEDIA": "Captura de red social",
    "MEME": "Meme",
    "INFOGRAPHIC": "Infografía",
    "ANIMAL_HEALTH_CONTENT": "Imagen de enfermedad animal",
    "PHOTOGRAPH": "Fotografía",
    "POTENTIALLY_MANIPULATED": "Posible manipulación",
}

MODEL_NAME = "vision_cnn"
MODEL_VERSION = "cnn32_64_64_dense64_v1"
INPUT_SIZE = 64
# 64→32 (pool) →16 (pool) →16 (conv3, sin pool) → flatten 16*16*64
FLATTEN_DIM = 64 * 16 * 16

ARCHITECTURE = [
    {"layer": "Input", "shape": "64×64×3"},
    {"layer": "Conv2D", "filters": 32, "kernel": "3×3", "activation": "ReLU"},
    {"layer": "MaxPool2D", "pool": "2×2"},
    {"layer": "Conv2D", "filters": 64, "kernel": "3×3", "activation": "ReLU"},
    {"layer": "MaxPool2D", "pool": "2×2"},
    {"layer": "Conv2D", "filters": 64, "kernel": "3×3", "activation": "ReLU"},
    {"layer": "Flatten", "units": FLATTEN_DIM},
    {"layer": "Dense", "units": 64, "activation": "ReLU"},
    {"layer": "Dense", "units": 8, "activation": "softmax"},
]

_SESSION: dict[str, Any] = {"net": None, "device": None, "loaded": False, "error": None}


def _torch_mod():
    import torch
    import torch.nn as nn
    import torch.nn.functional as F

    return torch, nn, F


class MiniCNN:
    """Conv32 → Pool → Conv64 → Pool → Conv64 → Flatten → Dense64 → Dense8."""

    @staticmethod
    def build(nn):  # noqa: ANN001
        class _Net(nn.Module):
            def __init__(self, n_classes: int = len(IMAGE_CLASSES)) -> None:
                super().__init__()
                self.conv1 = nn.Conv2d(3, 32, kernel_size=3, padding=1)
                self.conv2 = nn.Conv2d(32, 64, kernel_size=3, padding=1)
                self.conv3 = nn.Conv2d(64, 64, kernel_size=3, padding=1)
                self.pool = nn.MaxPool2d(2, 2)
                self.fc1 = nn.Linear(FLATTEN_DIM, 64)
                self.fc2 = nn.Linear(64, n_classes)

            def forward(self, x):  # noqa: ANN001
                x = self.pool(nn.functional.relu(self.conv1(x)))
                x = self.pool(nn.functional.relu(self.conv2(x)))
                x = nn.functional.relu(self.conv3(x))
                x = x.reshape(x.size(0), -1)
                x = nn.functional.relu(self.fc1(x))
                return self.fc2(x)

        return _Net()


def _tensor_from_path(path: str):
    torch, _nn, _F = _torch_mod()
    from PIL import Image
    import numpy as np

    img = Image.open(path).convert("RGB").resize((INPUT_SIZE, INPUT_SIZE))
    arr = np.asarray(img, dtype="float32") / 255.0
    tensor = torch.from_numpy(arr).permute(2, 0, 1).unsqueeze(0)
    return tensor


def reset_session() -> None:
    _SESSION["net"] = None
    _SESSION["device"] = None
    _SESSION["loaded"] = False
    _SESSION["error"] = None


def load_network(weights: Path | None = None):
    weights = Path(weights or CNN_WEIGHTS)
    if _SESSION["net"] is not None and _SESSION["loaded"]:
        return _SESSION["net"], _SESSION["device"]
    torch, nn, _F = _torch_mod()
    device = torch.device("cpu")
    net = MiniCNN.build(nn)
    net.to(device)
    net.eval()
    if weights.is_file():
        try:
            state = torch.load(str(weights), map_location=device, weights_only=False)
        except TypeError:
            state = torch.load(str(weights), map_location=device)
        if isinstance(state, dict) and "state_dict" in state:
            net.load_state_dict(state["state_dict"])
        else:
            net.load_state_dict(state)
        _SESSION["loaded"] = True
        _SESSION["error"] = None
    else:
        _SESSION["loaded"] = False
        _SESSION["error"] = f"missing_weights:{weights}"
    _SESSION["net"] = net
    _SESSION["device"] = device
    return net, device


def _pil_size(path: str) -> tuple[int, int]:
    try:
        from PIL import Image

        img = Image.open(path)
        return img.size
    except Exception:
        return 0, 0


class ImageClassifier:
    classes = IMAGE_CLASSES

    def __init__(self, model_version: str = MODEL_VERSION) -> None:
        self.model_name = MODEL_NAME
        self.model_version = model_version
        self.implemented = True

    def predict(self, path: str, url: str = "") -> dict[str, Any]:
        w, h = _pil_size(path)
        try:
            net, device = load_network()
            torch, _nn, F = _torch_mod()
            tensor = _tensor_from_path(path).to(device)
            with torch.no_grad():
                logits = net(tensor)
                probs = F.softmax(logits, dim=1)[0].tolist()
            scores = {name: float(p) for name, p in zip(IMAGE_CLASSES, probs)}
            label = max(scores, key=scores.get)
            loaded = bool(_SESSION.get("loaded"))
            return {
                "class": label,
                "class_index": IMAGE_CLASSES.index(label),
                "label_es": CLASS_LABELS_ES.get(label, label),
                "scores": {k: round(v, 4) for k, v in scores.items()},
                "confidence": round(float(scores[label]), 4),
                "width": w,
                "height": h,
                "model_name": self.model_name,
                "model_version": MODEL_VERSION if loaded else "cnn32_64_64_untrained",
                "implemented": True,
                "forward_pass": True,
                "weights_loaded": loaded,
                "weights_path": str(CNN_WEIGHTS),
                "note": "Clase visual (tipo de imagen), no veredicto de verdad. pHash/OCR van aparte.",
                "source_url": url,
            }
        except Exception as exc:
            return {
                "class": "PHOTOGRAPH",
                "class_index": IMAGE_CLASSES.index("PHOTOGRAPH"),
                "label_es": CLASS_LABELS_ES["PHOTOGRAPH"],
                "scores": {name: (1.0 if name == "PHOTOGRAPH" else 0.0) for name in IMAGE_CLASSES},
                "confidence": 0.0,
                "width": w,
                "height": h,
                "model_name": self.model_name,
                "model_version": "cnn_error",
                "implemented": False,
                "forward_pass": False,
                "error": str(exc)[:240],
                "note": "PyTorch no pudo ejecutar el forward. Instala torch (cpu).",
            }


def classify_image(path: str, url: str = "") -> dict[str, Any]:
    """Producción: CLIP/ResNet/URL. La MiniCNN queda como respaldo académico."""
    try:
        from visual_encoder import classify_visual

        return classify_visual(path, url=url)
    except Exception:
        return ImageClassifier().predict(path, url=url)
