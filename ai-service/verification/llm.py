"""LLM evidence-first — Ollama / OpenAI / Anthropic. NUNCA decide la verdad solo.

Reutiliza el contrato de the-newsbreakers/api/ai_verifier.py:
  extract claims, search queries, summarize evidence, explain.
Si el LLM no está, cae al verificador local de solapamiento de tokens
y el UI debe mostrar «LLM: no disponible».
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

_FW = Path(__file__).resolve().parents[2]
if str(_FW) not in sys.path:
    sys.path.insert(0, str(_FW))
from bootstrap import LEGACY_API, ensure_paths  # noqa: E402

ensure_paths()

HEADERS_JSON = {"Content-Type": "application/json"}
TIMEOUT = 45.0
OLLAMA_TIMEOUT = 90.0

SYSTEM_PROMPT = """Eres un analista de vigilancia zoosanitaria.
Usas SOLO los FRAGMENTOS de evidencia que te pasan. Nunca inventes hechos.
Nunca declares una noticia verdadera o falsa por tu cuenta: resume evidencia.
Responde SOLO JSON válido, sin markdown."""

EXTRACT_PROMPT = """Extrae afirmaciones verificables del texto.
JSON: {"claims":[{"text":"...","subject":"...","predicate":"...","object":"...","location":"","animal":""}],"search_queries":["..."]}
Máximo 4 claims. search_queries para WOAH/OMS/SENASICA/FAO."""

EXPLAIN_PROMPT = """Compara la AFIRMACIÓN con los FRAGMENTOS.
JSON: {"ai_verdict":"supports|contradicts|insufficient","confidence":0.0,"reasoning":"...","matched_facts":["..."],"summary":"..."}
Reglas: supports = los fragmentos respaldan; contradicts = los desmienten; insufficient = no alcanza.
Sé conservador. El LLM no es la verdad: solo explica la evidencia."""


def _load_env() -> None:
    for env_file in (LEGACY_API / ".env", _FW / ".env"):
        if not env_file.is_file():
            continue
        for raw in env_file.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip().strip("\"'")
            if key and key not in os.environ:
                os.environ[key] = value


_load_env()


def _token_overlap(a: str, b: str, min_len: int = 5) -> float:
    ta = {w for w in re.findall(r"\w+", a.lower()) if len(w) >= min_len}
    tb = {w for w in re.findall(r"\w+", b.lower()) if len(w) >= min_len}
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / max(len(ta), 1)


def _parse_llm_json(text: str) -> dict[str, Any] | None:
    text = (text or "").strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", text)
        if not m:
            return None
        try:
            data = json.loads(m.group(0))
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            return None


def _resolve_provider() -> tuple[str, dict[str, str]] | None:
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    if openai_key:
        return "openai", {"api_key": openai_key, "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini")}
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if anthropic_key:
        return "anthropic", {
            "api_key": anthropic_key,
            "model": os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-20241022"),
        }
    ollama_model = os.getenv("OLLAMA_MODEL", "").strip() or os.getenv("OLLAMA_DEFAULT_MODEL", "").strip()
    ollama_url = (os.getenv("OLLAMA_BASE_URL", "") or "http://127.0.0.1:11434").rstrip("/")
    # Probe even without OLLAMA_MODEL — llama3 / mistral / qwen if listed
    return "ollama", {"base_url": ollama_url, "model": ollama_model or "llama3"}


def probe_llm() -> dict[str, Any]:
    """Estado honesto para el dashboard."""
    try:
        import httpx
    except Exception:
        return {"available": False, "provider": None, "status": "LLM: no disponible", "reason": "httpx"}
    provider_info = _resolve_provider()
    if not provider_info:
        return {"available": False, "provider": None, "status": "LLM: no disponible", "reason": "no_provider"}
    provider, cfg = provider_info
    if provider != "ollama":
        return {
            "available": True,
            "provider": provider,
            "model": cfg.get("model"),
            "status": f"LLM: {provider}",
        }
    try:
        with httpx.Client(timeout=4.0) as client:
            r = client.get(f"{cfg['base_url']}/api/tags")
            r.raise_for_status()
            models = [m.get("name", "") for m in r.json().get("models", [])]
        chosen = cfg["model"]
        if models and chosen not in models and not any(chosen in m for m in models):
            chosen = models[0]
        return {
            "available": bool(models),
            "provider": "ollama",
            "model": chosen if models else cfg["model"],
            "models": models[:8],
            "status": f"LLM: ollama/{chosen}" if models else "LLM: no disponible",
            "reason": None if models else "ollama_sin_modelos",
        }
    except Exception as exc:
        return {
            "available": False,
            "provider": "ollama",
            "status": "LLM: no disponible",
            "reason": str(exc)[:160],
        }


def _call_ollama(cfg: dict[str, str], system: str, user: str) -> str:
    import httpx

    with httpx.Client(timeout=OLLAMA_TIMEOUT) as client:
        r = client.post(
            f"{cfg['base_url']}/api/chat",
            json={
                "model": cfg["model"],
                "stream": False,
                "format": "json",
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
        )
        r.raise_for_status()
        return r.json().get("message", {}).get("content", "")


def _call_openai(cfg: dict[str, str], system: str, user: str) -> str:
    import httpx

    with httpx.Client(timeout=TIMEOUT) as client:
        r = client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={**HEADERS_JSON, "Authorization": f"Bearer {cfg['api_key']}"},
            json={
                "model": cfg["model"],
                "temperature": 0.1,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]


def _chat(system: str, user: str) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    status = probe_llm()
    if not status.get("available"):
        return None, status
    provider = status.get("provider") or "ollama"
    cfg = {"model": status.get("model") or "llama3", "base_url": os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")}
    if provider == "openai":
        cfg["api_key"] = os.getenv("OPENAI_API_KEY", "")
    try:
        if provider == "openai":
            raw = _call_openai(cfg, system, user)
        else:
            raw = _call_ollama(cfg, system, user)
        parsed = _parse_llm_json(raw)
        return parsed, status
    except Exception as exc:
        status = {**status, "available": False, "status": "LLM: no disponible", "reason": str(exc)[:160]}
        return None, status


def local_overlap_explain(claim_text: str, snippets: list[dict[str, str]]) -> dict[str, Any]:
    """Fallback del ai_verifier.py — token overlap, no LLM."""
    main = claim_text[:600]
    best_support = 0.0
    best_snippet: dict[str, str] | None = None
    matched: set[str] = set()
    for s in snippets:
        combined = f"{s.get('title', '')} {s.get('snippet', '')}"
        score = _token_overlap(main, combined)
        if score > best_support:
            best_support = score
            best_snippet = s
            matched = {
                w for w in re.findall(r"\w+", main.lower()) if len(w) >= 5 and w in combined.lower()
            }
    if best_support >= 0.2:
        verdict, confidence = "supports", min(0.72, 0.32 + best_support * 0.55)
        reasoning = (
            f"Análisis local: solapamiento ({best_support:.0%}) con "
            f"{(best_snippet or {}).get('title') or 'catálogo oficial'}. No sustituye revisión humana."
        )
    else:
        verdict, confidence = "insufficient", max(0.12, best_support * 0.6)
        reasoning = "Análisis local: poco solapamiento con la evidencia; no hay base para confirmar ni desmentir."
    facts = []
    if matched:
        facts.append("Términos compartidos: " + ", ".join(sorted(matched)[:5]))
    return {
        "available": True,
        "provider": "local",
        "analysis_type": "local",
        "model": "token-overlap",
        "ai_verdict": verdict,
        "confidence": round(confidence, 3),
        "reasoning": reasoning,
        "summary": reasoning,
        "matched_facts": facts[:5],
        "status": "LLM: no disponible",
        "llm_used": False,
    }


def explain_with_evidence(
    claim_text: str,
    claims: dict[str, Any] | None = None,
    snippets: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Explica claim vs evidencia. LLM si vive; si no, overlap local."""
    claims = claims or {}
    snippets = snippets or []
    local = local_overlap_explain(claim_text, [{k: str(s.get(k) or "") for k in ("title", "snippet", "url")} for s in snippets])
    blocks = []
    for i, s in enumerate(snippets[:6], 1):
        blocks.append(f"[{i}] {s.get('url', '')}\n{s.get('snippet', '')[:500]}")
    user = (
        f"AFIRMACIÓN:\n{(claims.get('main_claim') or claim_text)[:600]}\n\n"
        f"FRAGMENTOS:\n" + ("\n\n".join(blocks) or "(sin fragmentos)")
    )
    parsed, status = _chat(SYSTEM_PROMPT + "\n" + EXPLAIN_PROMPT, user)
    if not parsed:
        local["probe"] = status
        return local
    verdict = str(parsed.get("ai_verdict", "insufficient")).lower()
    if verdict not in ("supports", "contradicts", "insufficient"):
        verdict = "insufficient"
    return {
        "available": True,
        "provider": status.get("provider"),
        "analysis_type": "llm",
        "model": status.get("model"),
        "ai_verdict": verdict,
        "confidence": round(max(0.0, min(1.0, float(parsed.get("confidence") or 0))), 3),
        "reasoning": str(parsed.get("reasoning") or "")[:800],
        "summary": str(parsed.get("summary") or parsed.get("reasoning") or "")[:800],
        "matched_facts": [str(f)[:200] for f in (parsed.get("matched_facts") or [])[:5]],
        "status": status.get("status") or f"LLM: {status.get('provider')}",
        "llm_used": True,
        "note": "El LLM explica evidencia; el NLI léxico decide el stance.",
    }


def llm_extract_claims(text: str) -> dict[str, Any] | None:
    parsed, status = _chat(SYSTEM_PROMPT + "\n" + EXTRACT_PROMPT, text[:2500])
    if not parsed:
        return None
    parsed["probe"] = status
    parsed["llm_used"] = True
    return parsed


def llm_search_queries(claim_text: str, diseases: list[str] | None = None) -> list[str]:
    diseases = diseases or []
    parsed, _status = _chat(
        SYSTEM_PROMPT,
        "Genera hasta 5 queries de búsqueda para fuentes oficiales (WOAH, WHO, FAO, SENASICA).\n"
        f"JSON: {{\"search_queries\":[\"...\"]}}\nAFIRMACIÓN: {claim_text[:400]}\nEnfermedades: {diseases}",
    )
    if not parsed:
        return []
    qs = parsed.get("search_queries") or []
    return [str(q) for q in qs if q][:5]


def try_legacy_verify(claim_text: str, claims: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any] | None:
    """Si el api viejo está en el path, úsalo tal cual."""
    try:
        from ai_verifier import verify_with_ai  # type: ignore

        return verify_with_ai(claim_text, claims, evidence)
    except Exception:
        return None
