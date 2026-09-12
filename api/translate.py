"""EN→ES for the dashboard. Cache first, then Google gtx, then MyMemory.

Ollama is optional (TNB_TRANSLATE_OLLAMA=1): lento y mezcla idiomas.
"""
from __future__ import annotations

import json
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any
from urllib.parse import quote

MYMEMORY_MAX = 500
MAX_TEXTS = 40
MAX_CHARS = 2500
OLLAMA_PROBE_S = 2.0
OLLAMA_BATCH_S = 12.0
OLLAMA_ONE_S = 8.0
MYMEMORY_S = 6.0
GTX_S = 8.0
GTX_WORKERS = 8

_ES_MARKERS = (
    " el ", " la ", " los ", " las ", " de ", " del ", " que ", " por ", " con ",
    " entre ", " para ", " una ", " unos ", " unas ", " afectado", " barrenador",
    " brote ", " gusano ",
)
_EN_MARKERS = (
    " the ", " and ", " with ", " from ", " found ", " this ", " first ",
    " outbreak ", " horse ", " ranch ", " traveling ", " declares ",
)

_OLLAMA_URL = lambda: (os.getenv("OLLAMA_BASE_URL") or "http://127.0.0.1:11434").rstrip("/")


def _ollama_model(listed: list[str] | None = None) -> str:
    chosen = (os.getenv("OLLAMA_MODEL") or os.getenv("OLLAMA_DEFAULT_MODEL") or "llama3").strip()
    if listed and chosen not in listed and not any(chosen in name for name in listed):
        return listed[0]
    return chosen or "llama3"


def _use_ollama() -> bool:
    return os.getenv("TNB_TRANSLATE_OLLAMA", "0").strip() in {"1", "true", "True", "yes"}


def probe_ollama() -> dict[str, Any]:
    if not _use_ollama():
        return {"available": False, "reason": "disabled"}
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


def _lang_hint(text: str) -> str:
    blob = f" {text.lower()} "
    es = sum(1 for m in _ES_MARKERS if m in blob)
    en = sum(1 for m in _EN_MARKERS if m in blob)
    if es >= 2 and es > en:
        return "es"
    if en >= 2 and en >= es:
        return "en"
    return "und"


def _clean(raw: str, source: str) -> str | None:
    text = (raw or "").strip()
    text = re.sub(r"^```(?:\w+)?\s*|\s*```$", "", text).strip()
    text = text.strip("\"'`")
    if not text or text == source.strip():
        return None
    if text.lower().startswith(("translation:", "traducción:", "traduccion:")):
        text = text.split(":", 1)[1].strip()
    if re.search(r"[\u0400-\u04FF\u3040-\u30FF\u4E00-\u9FFF]", text) and re.search(
        r"[A-Za-záéíóúüñ]", text, re.I
    ):
        return None
    src_hint = _lang_hint(source)
    out_hint = _lang_hint(text)
    if src_hint == "en" and out_hint == "en":
        return None
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


def _ollama_one(text: str, cfg: dict[str, Any]) -> str | None:
    try:
        import httpx
    except Exception:
        return None
    prompt = (
        "Translate the following text to Spanish. "
        "Return only the Spanish translation, with no quotes or preface.\n\n"
        f"{text}"
    )
    try:
        with httpx.Client(timeout=OLLAMA_ONE_S) as client:
            r = client.post(
                f"{cfg['base_url']}/api/generate",
                json={"model": cfg["model"], "prompt": prompt, "stream": False},
            )
            r.raise_for_status()
            raw = (r.json() or {}).get("response") or ""
        return _clean(raw, text)
    except Exception:
        return None


def _google_gtx_one(text: str) -> str | None:
    if not text.strip():
        return None
    try:
        import httpx
    except Exception:
        return None
    url = "https://translate.googleapis.com/translate_a/single"
    try:
        with httpx.Client(timeout=GTX_S) as client:
            r = client.get(
                url,
                params={"client": "gtx", "sl": "en", "tl": "es", "dt": "t", "q": text[:4500]},
            )
            r.raise_for_status()
            data = r.json()
        chunks = data[0] if isinstance(data, list) and data else []
        translated = "".join(str(part[0]) for part in chunks if part and part[0])
        return _clean(translated, text)
    except Exception:
        return None


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


def _gtx_many(texts: list[str]) -> list[str | None]:
    if not texts:
        return []
    out: list[str | None] = [None] * len(texts)
    with ThreadPoolExecutor(max_workers=min(GTX_WORKERS, len(texts))) as pool:
        futures = {pool.submit(_google_gtx_one, texts[i]): i for i in range(len(texts))}
        for fut in as_completed(futures):
            idx = futures[fut]
            try:
                out[idx] = fut.result()
            except Exception:
                out[idx] = None
    return out


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
            if not src.strip() or _lang_hint(src) == "es":
                out.append(src)
                continue
            hit = store.get_translation(src)
            if hit is not None:
                out.append(hit)
            else:
                out.append(src)
                pending.append(i)

        sources = {i: ("" if limited[i] is None else str(limited[i])[:MAX_CHARS]) for i in pending}

        if pending:
            batch = _gtx_many([sources[i] for i in pending])
            still: list[int] = []
            for i, translated in zip(pending, batch):
                if translated:
                    store.put_translation(sources[i], translated, "gtx")
                    out[i] = translated
                else:
                    still.append(i)
            pending = still

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
            if ollama.get("available"):
                translated = _ollama_one(src, ollama)
                if translated:
                    store.put_translation(src, translated, "ollama")
                    out[i] = translated
                    continue
            if memory_fails < 2:
                translated = _mymemory_one(src)
                if translated:
                    memory_fails = 0
                    store.put_translation(src, translated, "mymemory")
                    out[i] = translated
                    continue
                if len(src) <= MYMEMORY_MAX:
                    memory_fails += 1
        extras = ["" if t is None else str(t)[:MAX_CHARS] for t in texts[MAX_TEXTS:]]
        return out + extras
    finally:
        if own:
            store.close()
