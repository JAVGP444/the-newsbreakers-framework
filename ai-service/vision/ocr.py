"""OCR — pytesseract, PaddleOCR o alt-text. Siempre guarda ocr_text (aunque vacío)."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_FW = Path(__file__).resolve().parents[2]
if str(_FW) not in sys.path:
    sys.path.insert(0, str(_FW))
from bootstrap import OCR_STUDIO_SRC, ensure_paths  # noqa: E402

ensure_paths()

MODEL_NAME = "ocr_observatory"


def _empty(alt_text: str = "", note: str = "") -> dict[str, Any]:
    return {
        "text": alt_text or "",
        "boxes": [],
        "language": "es",
        "engine": "alt_text" if alt_text else "none",
        "model_name": MODEL_NAME,
        "model_version": "ocr_uninstalled" if not alt_text else "alt_text",
        "implemented": bool(alt_text),
        "note": note or "Sin motor OCR; se guarda alt text o cadena vacía.",
    }


def _pytesseract(path: str) -> dict[str, Any] | None:
    try:
        import pytesseract
        from PIL import Image
    except Exception:
        return None
    try:
        img = Image.open(path)
        text = pytesseract.image_to_string(img, lang="spa+eng") or pytesseract.image_to_string(img)
        text = (text or "").strip()
        return {
            "text": text,
            "boxes": [],
            "language": "es",
            "engine": "pytesseract",
            "model_name": MODEL_NAME,
            "model_version": "pytesseract",
            "implemented": True,
        }
    except Exception as exc:
        return {
            "text": "",
            "boxes": [],
            "language": "es",
            "engine": "pytesseract_error",
            "model_name": MODEL_NAME,
            "model_version": "pytesseract",
            "implemented": False,
            "note": str(exc)[:200],
        }


def _paddle(path: str) -> dict[str, Any] | None:
    try:
        from paddleocr import PaddleOCR  # type: ignore
    except Exception:
        return None
    try:
        ocr = PaddleOCR(lang="es", show_log=False)
        result = ocr.ocr(path, cls=True)
        lines: list[str] = []
        boxes: list[dict[str, Any]] = []
        for page in result or []:
            for row in page or []:
                txt = row[1][0] if row and len(row) > 1 else ""
                if txt:
                    lines.append(str(txt))
                    boxes.append({"text": txt, "bbox": row[0] if row else None})
        return {
            "text": "\n".join(lines),
            "boxes": boxes,
            "language": "es",
            "engine": "paddleocr",
            "model_name": MODEL_NAME,
            "model_version": "paddleocr",
            "implemented": True,
        }
    except Exception as exc:
        return {
            "text": "",
            "boxes": [],
            "language": "es",
            "engine": "paddleocr_error",
            "model_name": MODEL_NAME,
            "model_version": "paddleocr",
            "implemented": False,
            "note": str(exc),
        }


def _studio_engine():
    from config.license import allows

    if not allows("ocr"):
        return None
    if not OCR_STUDIO_SRC.is_dir():
        return None
    try:
        from document_intelligence_studio.screen_copilot.ocr_engine import OCREngine

        return OCREngine()
    except Exception:
        return None


class DocumentOCR:
    def __init__(self, lang: str = "es") -> None:
        self.lang = lang
        self.model_name = MODEL_NAME

    def read(self, path: str, alt_text: str = "") -> dict[str, Any]:
        tess = _pytesseract(path)
        if tess and tess.get("implemented") and (tess.get("text") or "").strip():
            return tess
        paddle = _paddle(path)
        if paddle and paddle.get("implemented") and (paddle.get("text") or "").strip():
            return paddle
        engine = _studio_engine()
        if engine is not None:
            try:
                from PIL import Image

                image = Image.open(path)
                result = engine.extract_full(image)
                text = (result.text or "").strip()
                if text:
                    return {
                        "text": text,
                        "boxes": [
                            {"text": getattr(line, "text", ""), "bbox": getattr(line, "bbox", None)}
                            for line in (result.lines or [])
                        ],
                        "language": self.lang,
                        "engine": getattr(engine, "backend_name", "studio"),
                        "model_name": self.model_name,
                        "model_version": getattr(engine, "backend_name", "studio"),
                        "implemented": True,
                        "confidence": result.confidence,
                    }
            except Exception:
                pass
        note = "Sin Tesseract/PaddleOCR; se guarda alt text o cadena vacía."
        if tess and tess.get("note"):
            note = str(tess.get("note"))
        out = _empty(alt_text, note=note)
        out["text"] = alt_text or ""
        return out


def ocr_image(path: str, lang: str = "es", alt_text: str = "") -> dict[str, Any]:
    result = DocumentOCR(lang=lang).read(path, alt_text=alt_text)
    result["text"] = result.get("text") or ""
    return result
