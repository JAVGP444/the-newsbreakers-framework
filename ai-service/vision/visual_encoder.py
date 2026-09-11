"""Codificador visual de producción: CLIP (si hay) o ResNet18 ImageNet.

La CNN académica 64×64 entrenada en dibujos NO es el modelo productivo.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from cnn import CLASS_LABELS_ES, IMAGE_CLASSES, ImageClassifier

ANIMAL_HEALTH_KWS = (
    "h5n1", "h5n2", "hpai", "influenza", "aviar", "avian", "gripe",
    "screwworm", "barrenador", "cochliomyia", "poultry", "aves", "ganado",
    "senasica", "woah", "wahis", "bioseguridad", "granja", "porcina", "swine",
)

IMAGENET_TO_CLASS = {
    "web site": "NEWS_SCREENSHOT",
    "menu": "OFFICIAL_DOCUMENT",
    "envelope": "OFFICIAL_DOCUMENT",
    "book jacket": "OFFICIAL_DOCUMENT",
    "binder": "OFFICIAL_DOCUMENT",
    "notebook": "OFFICIAL_DOCUMENT",
    "comic book": "MEME",
    "hen": "ANIMAL_HEALTH_CONTENT",
    "cock": "ANIMAL_HEALTH_CONTENT",
    "ox": "ANIMAL_HEALTH_CONTENT",
    "hog": "ANIMAL_HEALTH_CONTENT",
    "pig": "ANIMAL_HEALTH_CONTENT",
    "cattle": "ANIMAL_HEALTH_CONTENT",
    "goose": "ANIMAL_HEALTH_CONTENT",
    "drake": "ANIMAL_HEALTH_CONTENT",
    "bee eater": "ANIMAL_HEALTH_CONTENT",
}

CLIP_PROMPTS = {
    "OFFICIAL_DOCUMENT": "an official government or veterinary PDF document, letterhead, stamp",
    "NEWS_SCREENSHOT": "a screenshot of a news website article",
    "SOCIAL_MEDIA": "a screenshot of a social media post with like buttons",
    "MEME": "an internet meme with bold caption text",
    "INFOGRAPHIC": "an infographic chart with icons and statistics",
    "ANIMAL_HEALTH_CONTENT": "a photograph of poultry, livestock or a farm animal disease",
    "PHOTOGRAPH": "a naturalistic photograph of a scene",
    "POTENTIALLY_MANIPULATED": "a digitally manipulated or photoshopped image",
}

_CLIP = {"model": None, "preprocess": None, "tokenizer": None, "error": None}
_RESNET = {"model": None, "weights": None, "error": None}


def animal_health_relevance(text: str) -> float:
    blob = (text or "").lower()
    if not blob:
        return 0.0
    hits = sum(1 for kw in ANIMAL_HEALTH_KWS if kw in blob)
    return round(min(1.0, hits / 4.0), 3)


def url_heuristic(url: str) -> dict[str, Any] | None:
    host = (urlparse(url or "").hostname or "").lower()
    path = (url or "").lower()
    if not host:
        return None
    if any(h in host for h in ("gob.mx", "woah.org", "who.int", "fao.org", "cdc.gov", "usda.gov", "paho.org")):
        return _pack("OFFICIAL_DOCUMENT", 0.78, "url_heuristic")
    if any(h in host for h in ("twitter.com", "x.com", "facebook.com", "instagram.com", "tiktok.com")):
        return _pack("SOCIAL_MEDIA", 0.76, "url_heuristic")
    if "youtube.com" in host or "youtu.be" in host or "ytimg.com" in host:
        return _pack("PHOTOGRAPH", 0.7, "url_heuristic")
    if any(tok in path for tok in ("meme", "funny")):
        return _pack("MEME", 0.65, "url_heuristic")
    return None


def _pack(label: str, conf: float, encoder: str, scores: dict[str, float] | None = None) -> dict[str, Any]:
    if not scores:
        rest = max(0.02, (1.0 - conf) / max(1, len(IMAGE_CLASSES) - 1))
        scores = {name: round(rest, 4) for name in IMAGE_CLASSES}
        scores[label] = round(conf, 4)
    return {
        "class": label,
        "class_index": IMAGE_CLASSES.index(label) if label in IMAGE_CLASSES else 6,
        "label_es": CLASS_LABELS_ES.get(label, label),
        "scores": scores,
        "confidence": round(float(scores[label]), 4),
        "encoder": encoder,
        "role": "production" if encoder != "academic_cnn" else "academic_experimental",
        "model_version": encoder,
        "implemented": True,
        "note": (
            "Codificador visual de producción (CLIP/ResNet/URL). "
            "No es detector de fake news."
            if encoder != "academic_cnn"
            else "CNN académica experimental (dibujos 64×64). No usar como métrica de producción."
        ),
    }


def _try_clip(path: str) -> dict[str, Any] | None:
    if os.environ.get("TNB_VISION", "1") == "0":
        return None
    try:
        import torch
        import open_clip
        from PIL import Image
    except Exception:
        return None
    try:
        if _CLIP["model"] is None:
            model, _, preprocess = open_clip.create_model_and_transforms("ViT-B-32", pretrained="laion2b_s34b_b79k")
            tokenizer = open_clip.get_tokenizer("ViT-B-32")
            model.eval()
            _CLIP["model"] = model
            _CLIP["preprocess"] = preprocess
            _CLIP["tokenizer"] = tokenizer
        model, preprocess, tokenizer = _CLIP["model"], _CLIP["preprocess"], _CLIP["tokenizer"]
        image = preprocess(Image.open(path).convert("RGB")).unsqueeze(0)
        texts = tokenizer(list(CLIP_PROMPTS.values()))
        with torch.no_grad():
            image_features = model.encode_image(image)
            text_features = model.encode_text(texts)
            image_features /= image_features.norm(dim=-1, keepdim=True)
            text_features /= text_features.norm(dim=-1, keepdim=True)
            logits = (100.0 * image_features @ text_features.T).softmax(dim=-1)[0].tolist()
        scores = {name: float(p) for name, p in zip(IMAGE_CLASSES, logits)}
        label = max(scores, key=scores.get)
        return _pack(label, float(scores[label]), "open_clip_vitb32", {k: round(v, 4) for k, v in scores.items()})
    except Exception as exc:
        _CLIP["error"] = str(exc)[:200]
        return None


def _try_resnet(path: str) -> dict[str, Any] | None:
    if os.environ.get("TNB_VISION", "1") == "0":
        return None
    try:
        import torch
        from PIL import Image
        from torchvision.models import ResNet18_Weights, resnet18
    except Exception:
        return None
    try:
        if _RESNET["model"] is None:
            weights = ResNet18_Weights.IMAGENET1K_V1
            net = resnet18(weights=weights)
            net.eval()
            _RESNET["model"] = net
            _RESNET["weights"] = weights
        weights = _RESNET["weights"]
        net = _RESNET["model"]
        img = Image.open(path).convert("RGB")
        batch = weights.transforms()(img).unsqueeze(0)
        with torch.no_grad():
            logits = net(batch)[0]
            probs = torch.softmax(logits, dim=0)
            topk = torch.topk(probs, 5)
        names = [weights.meta["categories"][i] for i in topk.indices.tolist()]
        mapped = "PHOTOGRAPH"
        conf = float(topk.values[0])
        for name in names:
            key = name.lower()
            for needle, label in IMAGENET_TO_CLASS.items():
                if needle in key:
                    mapped = label
                    break
            else:
                continue
            break
        return _pack(mapped, max(0.45, min(0.88, conf)), "resnet18_imagenet")
    except Exception as exc:
        _RESNET["error"] = str(exc)[:200]
        return None


def classify_visual(path: str, url: str = "", ocr_text: str = "") -> dict[str, Any]:
    """Modelo productivo (CLIP/ResNet/URL) con CNN académica solo como respaldo."""
    w, h = 0, 0
    try:
        from PIL import Image

        w, h = Image.open(path).size
    except Exception:
        pass
    heur = url_heuristic(url)
    clip = _try_clip(path)
    resnet = None if clip else _try_resnet(path)
    academic = ImageClassifier().predict(path, url=url)
    primary = clip or resnet or heur
    if primary is None:
        primary = {
            "class": None,
            "class_index": None,
            "label_es": "Sin encoder de producción",
            "scores": {},
            "confidence": None,
            "encoder": "unavailable",
            "role": "production",
            "model_version": "unavailable",
            "implemented": False,
            "weights_loaded": False,
            "note": (
                "CLIP/ResNet no está disponible. La CNN académica no es el resultado principal "
                "ni un veredicto de verdad."
            ),
        }
    elif heur and heur["class"] == "OFFICIAL_DOCUMENT" and primary.get("class") not in {"OFFICIAL_DOCUMENT", "NEWS_SCREENSHOT"}:
        primary = heur
    relevance = animal_health_relevance(f"{ocr_text} {url}")
    if relevance >= 0.5 and primary.get("class") == "PHOTOGRAPH":
        primary = dict(primary)
        primary["class"] = "ANIMAL_HEALTH_CONTENT"
        primary["label_es"] = CLASS_LABELS_ES["ANIMAL_HEALTH_CONTENT"]
        primary["class_index"] = IMAGE_CLASSES.index("ANIMAL_HEALTH_CONTENT")
        scores = dict(primary.get("scores") or {})
        scores["ANIMAL_HEALTH_CONTENT"] = max(float(scores.get("ANIMAL_HEALTH_CONTENT") or 0), 0.55)
        primary["scores"] = scores
    primary["width"] = w
    primary["height"] = h
    primary["source_url"] = url
    primary["academic"] = {
        "class": academic.get("class"),
        "label_es": academic.get("label_es"),
        "confidence": academic.get("confidence"),
        "scores": academic.get("scores"),
        "weights_loaded": academic.get("weights_loaded"),
        "model_version": academic.get("model_version"),
        "role": "academic_experimental",
        "note": "CNN académica experimental (64×64). No es el modelo de producción ni un veredicto de verdad.",
    }
    primary["production"] = {
        "encoder": primary.get("encoder"),
        "class": primary.get("class"),
        "label_es": primary.get("label_es"),
        "confidence": primary.get("confidence"),
        "scores": primary.get("scores"),
        "available": primary.get("encoder") not in {None, "unavailable", "academic_cnn"},
    }
    primary["animal_health_relevance"] = relevance
    primary["weights_loaded"] = bool(primary.get("encoder") not in {None, "unavailable"})
    return primary


def classify_image(path: str, url: str = "") -> dict[str, Any]:
    return classify_visual(path, url=url)
