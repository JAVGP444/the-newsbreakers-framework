"""EN→ES for the dashboard. Cache first, then Ollama, then MyMemory (short)."""
from __future__ import annotations

import json
import os
import re
from typing import Any
from urllib.parse import quote

MYMEMORY_MAX = 500
MAX_TEXTS = 40
MAX_CHARS = 4000
OLLAMA_PROBE_S = 3.0
OLLAMA_BATCH_S = 20.0
MYMEMORY_S = 6.0

_OLLAMA_URL = lambda: (os.getenv("OLLAMA_BASE_URL") or "http://127.0.0.1:11434").rstrip("/")


def _ollama_model(listed: list[str] | None = None) -> str:
    chosen = (os.getenv("OLLAMA_MODEL") or os.getenv("OLLAMA_DEFAULT_MODEL") or "llama3").strip()
    if listed and chosen not in listed and not any(chosen in name for name in listed):
        return listed[0]
    return chosen or "llama3"


def probe_ollama() -> dict[str, Any]:
    try:
        import httpx
    except Exception:
        return {"available": False, "reason": "httpx"}
    try:
        with httpx.Client(timeout=OLLAMA_PROBE_S) as client:
            r = client.get(f"{_OLLAMA_URL()}/api/tags")
            r.raise_for_status()
            models = [m.get("name", "") for m in (r.json() or {}).get("models", [])]
        if not models:
            return {"available": False, "reason": "ollama_sin_modelos"}
        return {"available": True, "model": _ollama_model(models), "base_url": _OLLAMA_URL()}
    except Exception as exc:
        return {"available": False, "reason": str(exc)[:160]}


def _clean(raw: str, source: str) -> str | None:
    text = (raw or "").strip()
    text = re.sub(r"^```(?:\w+)?\s*|\s*```$", "", text).strip()
    text = text.strip("\"'`")
    if not text or text == source.strip():
        return None
    if text.lower().startswith(("translation:", "traducción:", "traduccion:")):
        text = text.split(":", 1)[1].strip()
    return text or None


def _ollama_batch(texts: list[str], cfg: dict[str, Any]) -> list[str | None]:
    if not texts:
        return []
    try:
        import httpx
    except Exception:
        return [None] * len(texts)
    prompt = (
        "Translate each English string in this JSON array to Spanish. "
        "Return ONLY a JSON array of Spanish strings, same length and order.\n\n"
        f"{json.dumps(texts, ensure_ascii=False)}"
    )
    try:
        with httpx.Client(timeout=OLLAMA_BATCH_S) as client:
            r = client.post(
                f"{cfg['base_url']}/api/generate",
                json={"model": cfg["model"], "prompt": prompt, "stream": False, "format": "json"},
            )
            r.raise_for_status()
            raw = (r.json() or {}).get("response") or ""
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            parsed = parsed.get("translations") or parsed.get("texts") or []
        if not isinstance(parsed, list) or len(parsed) != len(texts):
            return [None] * len(texts)
        return [_clean(str(item or ""), src) for item, src in zip(parsed, texts)]
    except Exception:
        return [None] * len(texts)


def _mymemory_one(text: str) -> str | None:
    if not text or len(text) > MYMEMORY_MAX:
        return None
    try:
        import httpx
    except Exception:
        return None
    url = f"https://api.mymemory.translated.net/get?q={quote(text, safe='')}&langpair=en|es"
    try:
        with httpx.Client(timeout=MYMEMORY_S) as client:
            r = client.get(url)
            r.raise_for_status()
            data = r.json() or {}
        translated = (data.get("responseData") or {}).get("translatedText") or ""
        if "MYMEMORY WARNING" in translated.upper():
            return None
        return _clean(translated, text)
    except Exception:
        return None


def translate_texts(texts: list[str], store=None) -> list[str]:
    from database.store import Store

    own = store is None
    store = store or Store()
    try:
        limited = list(texts)[:MAX_TEXTS]
        out: list[str] = []
        pending: list[int] = []
        for i, raw in enumerate(limited):
            src = "" if raw is None else str(raw)[:MAX_CHARS]
            if not src.strip():
                out.append(src)
                continue
            hit = store.get_translation(src)
            if hit is not None:
                out.append(hit)
            else:
                out.append(src)
                pending.append(i)

        sources = {i: ("" if limited[i] is None else str(limited[i])[:MAX_CHARS]) for i in pending}
        ollama = probe_ollama() if pending else {"available": False}
        if ollama.get("available") and pending:
            batch = _ollama_batch([sources[i] for i in pending], ollama)
            still: list[int] = []
            for i, translated in zip(pending, batch):
                if translated:
                    store.put_translation(sources[i], translated, "ollama")
                    out[i] = translated
                else:
                    still.append(i)
            pending = still

        memory_fails = 0
        for i in pending:
            src = sources[i]
            translated = None
            if memory_fails < 2:
                translated = _mymemory_one(src)
                if translated:
                    memory_fails = 0
                    store.put_translation(src, translated, "mymemory")
                    out[i] = translated
                    continue
                if len(src) <= MYMEMORY_MAX:
                    memory_fails += 1
            out[i] = src
        extras = ["" if t is None else str(t)[:MAX_CHARS] for t in texts[MAX_TEXTS:]]
        return out + extras
    finally:
        if own:
            store.close()
