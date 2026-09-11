"""Ciclo completo del pipeline multimodal (MVP ejecutable)."""
from __future__ import annotations

import argparse
import hashlib
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

_FW = Path(__file__).resolve().parents[1]
if str(_FW) not in sys.path:
    sys.path.insert(0, str(_FW))
from bootstrap import FRAMEWORK_ROOT, IMAGES_DIR, PROJECT_ROOT, ensure_paths  # noqa: E402

ensure_paths()

from access import resolve_access, scrape_deferred_note  # noqa: E402
from api_fetcher import fetch_source_api  # noqa: E402
from claims import extract_claims  # noqa: E402
from database.store import Store, append_raw  # noqa: E402
from dedup import DedupIndex  # noqa: E402
from engine import cluster_claims  # noqa: E402
from entities import extract_entities  # noqa: E402
from import_corpus import inject_corpus  # noqa: E402
from language import detect_language  # noqa: E402
from llm import explain_with_evidence, probe_llm  # noqa: E402
from nli import verify_claim  # noqa: E402
from process import process_image, write_placeholder_png  # noqa: E402
from relevance import classify_topic, should_skip  # noqa: E402
from retrieve import retrieve_evidence  # noqa: E402
from risk_engine import claim_severity_score, risk_score, source_unreliability  # noqa: E402
from rss_fetcher import fetch_source_rss  # noqa: E402
from source_catalog import (  # noqa: E402
    backoff_next_check,
    frequency_minutes,
    load_catalog,
    merge_runtime,
    next_check,
    sources_due,
)
from workers.queues import QUEUE_IMAGE, QUEUE_INGEST, QUEUE_NLP, drain, enqueue  # noqa: E402

ALERT_THRESHOLD = int(os.environ.get("TNB_ALERT_THRESHOLD", "55"))
MAX_SOURCES = int(os.environ.get("TNB_MAX_SOURCES", "12"))
RETRY_FAST = os.environ.get("TNB_FAST", "0") == "1"
RETRY_WAITS = (2.0, 5.0) if RETRY_FAST else (30.0, 120.0)


def _want_demo_seed(explicit: bool = False) -> bool:
    if explicit:
        return True
    return os.environ.get("TNB_DEMO_SEED", "0").strip() == "1"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _retry_fetch(source: dict[str, Any], method: str) -> tuple[list[Any], str | None]:
    last_error = None
    for attempt in range(3):
        try:
            if method == "rss":
                return fetch_source_rss(source, delay=True), None
            if method == "api":
                return fetch_source_api(source), None
            return [], "unsupported method"
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
            if attempt < 2:
                time.sleep(RETRY_WAITS[attempt])
    return [], last_error


DEMO_ARTICLES = [
    {
        "source_id": "SRC002",
        "url": "https://www.woah.org/",
        "title": "WOAH confirma un brote de influenza aviar H5N1 en aves de corral",
        "text": (
            "La Organización Mundial de Sanidad Animal (WOAH/OMSA) confirma un brote de "
            "gripe aviar H5N1 altamente patógena en aves de corral. SENASICA mantiene "
            "vigilancia epidemiológica. Casos confirmados en granjas avícolas."
        ),
        "images": [],
        "raw_format": "fixture",
    },
    {
        "source_id": "SRC-FAO",
        "url": "https://www.fao.org/animal-production/en",
        "title": "FAO: vigilancia de influenza aviar y bioseguridad en granjas",
        "text": (
            "La FAO publica orientación de bioseguridad para productores avícolas ante "
            "reportes de influenza aviar H5N1. La confirmación de laboratorio corresponde "
            "a los servicios veterinarios oficiales y a WOAH/WAHIS."
        ),
        "images": [],
        "raw_format": "fixture",
    },
    {
        "source_id": "SRC001",
        "url": "",
        "title": "Dicen que las autoridades ocultan el brote y que la vacuna causa la enfermedad",
        "text": (
            "Un mensaje en redes afirma que SENASICA oculta un brote de gusano barrenador "
            "y que la vacuna causa la enfermedad porque fue creada artificialmente en un laboratorio. "
            "No hay URL oficial: la ficha se abre solo dentro del observatorio."
        ),
        "images": [],
        "raw_format": "fixture",
    },
]


def inject_demo_seed(store: Store, index: DedupIndex) -> list[dict[str, Any]]:
    colors = [(180, 40, 40), (40, 80, 160), (40, 140, 70)]
    created = []
    for i, raw in enumerate(DEMO_ARTICLES):
        from normalize import to_universal

        demo_img = IMAGES_DIR / f"demo_seed_{i}.png"
        write_placeholder_png(demo_img, colors[i % len(colors)])
        item = to_universal(
            source_id=raw["source_id"],
            url=raw["url"],
            title=raw["title"],
            text=raw["text"],
            images=[str(demo_img)] if demo_img.exists() else [],
            raw_format="fixture",
        )
        dup, _reason = index.register(item.url, f"{item.title} {item.text}")
        if dup:
            continue
        created.append(item.to_dict())
    store.audit("cycle", "seed", "demo_seed", {"count": len(created)})
    return created


def _article_nli_label(claims: list[dict[str, Any]]) -> str:
    labels = [c.get("nli_label") for c in claims]
    if labels.count("Contradicted") > labels.count("Supported"):
        return "Contradicted"
    if "Supported" in labels:
        return "Supported"
    return "Unknown"


def analyze_article(
    store: Store,
    item: dict[str, Any],
    source: dict[str, Any],
    image_jobs: list[dict[str, Any]],
    llm_probe: dict[str, Any] | None = None,
    llm_budget: list[int] | None = None,
) -> dict[str, Any]:
    text = f"{item.get('title') or ''} {item.get('text') or ''}"
    topic = classify_topic(text)
    if topic["skip"] and item.get("raw_format") not in {"youtube", "social", "corpus", "fixture"}:
        store.audit("article", item["content_id"], "relevance_skip", topic)
        return {"skipped": True, "reason": "relevance", "relevance": topic["relevance"]}

    lang = item.get("language") if item.get("language") not in (None, "", "und") else detect_language(text)
    countries = [e["value"] for e in extract_entities(text, topic.get("diseases")) if e["kind"] == "COUNTRY"]
    country = item.get("country") or (countries[0] if countries else "XX")

    store.insert_article(
        {
            **item,
            "language": lang,
            "country": country,
            "source_type": item.get("source_type") or source.get("type"),
            "disease_tags": item.get("disease_tags") or topic.get("diseases") or [],
            "relevance_score": topic["relevance"],
            "pipeline_level": 2,
            "llm_status": (llm_probe or {}).get("status") or "LLM: no disponible",
            "model_versions": {
                **(item.get("model_versions") or {}),
                "relevance": topic["model_version"],
                "language": "langdetect_v1",
            },
        }
    )
    enqueue(QUEUE_INGEST, {"content_id": item["content_id"], "source_id": item.get("source_id")})
    enqueue(QUEUE_NLP, {"content_id": item["content_id"], "text": text})

    entities = extract_entities(text, topic.get("diseases"))
    for ent in entities:
        ent["content_id"] = item["content_id"]
        ent["entity_id"] = "ENT-" + hashlib.sha256(
            f"{item['content_id']}:{ent['kind']}:{ent['value']}".encode()
        ).hexdigest()[:16]
        store.insert_entity(ent)

    body = (item.get("text") or "").strip()
    packed: dict[str, Any] = {"claims": [], "main_claim": "", "model_name": "skipped_short_text", "model_version": "len400"}
    if len(body) < 400:
        store.update_article_analysis(item["content_id"], pipeline_level=1)
        store.audit("article", item["content_id"], "claims_skipped_short_text", {"chars": len(body)})
    else:
        packed = extract_claims(text, topic.get("diseases"))
    claims_out = []
    for claim in packed.get("claims") or []:
        claim["content_id"] = item["content_id"]
        evidence = retrieve_evidence(claim)
        nli = verify_claim(claim, evidence)
        claim["nli_label"] = nli["label"]
        claim["confidence"] = nli["confidence"]
        claim["model_name"] = packed.get("model_name")
        claim["model_version"] = packed.get("model_version")
        claim["verdict"] = nli["label"]
        store.insert_claim(claim)
        for ev in evidence:
            ev["claim_id"] = claim["claim_id"]
            store.insert_evidence(ev)
        store.audit(
            "claim",
            claim["claim_id"],
            "nli",
            {"label": nli["label"], "evidence": len(evidence), "note": nli.get("note")},
        )
        claims_out.append(claim)

    llm_probe = llm_probe or {"available": False, "status": "LLM: no disponible", "provider": None}
    snippets = store.list_evidence(claims_out[0]["claim_id"]) if claims_out else []
    use_remote = bool(llm_probe.get("available")) and (llm_budget is None or llm_budget[0] > 0)
    if use_remote:
        if llm_budget is not None:
            llm_budget[0] -= 1
        explanation = explain_with_evidence(packed.get("main_claim") or text, packed, snippets)
    else:
        from llm import local_overlap_explain

        explanation = local_overlap_explain(
            packed.get("main_claim") or text,
            [{k: str(s.get(k) or "") for k in ("title", "snippet", "url")} for s in snippets],
        )
        explanation["status"] = llm_probe.get("status") or "LLM: no disponible"
        explanation["probe"] = llm_probe

    imgs = list(item.get("images") or [])
    alts = list(item.get("image_alts") or [])
    for i, url in enumerate(imgs[:4]):
        job = {
            "content_id": item["content_id"],
            "url": url,
            "alt_text": alts[i] if i < len(alts) else "",
        }
        enqueue(QUEUE_IMAGE, job)
        image_jobs.append(job)

    nli_label = _article_nli_label(claims_out)
    signals = {
        "nli_label": nli_label,
        "evidence_contradiction": 90 if nli_label == "Contradicted" else (10 if nli_label == "Supported" else 40),
        "source_reliability": source_unreliability(source),
        "image_reuse": 0,
        "claim_severity": claim_severity_score(claims_out),
        "alert_threshold": ALERT_THRESHOLD,
        "low_confidence": nli_label == "Unknown" and topic["relevance"] >= 0.8,
    }
    risk = risk_score(signals)
    store.update_article_analysis(
        item["content_id"],
        relevance_score=topic["relevance"],
        pipeline_level=9 if risk["verdict"] == "REVISIÓN HUMANA" else 8,
        risk_score=risk["risk_score"],
        verdict=risk["verdict"],
        language=lang,
        country=country,
        llm_status=explanation.get("status") or llm_probe.get("status"),
        llm_explanation=explanation.get("reasoning") or explanation.get("summary") or "",
        llm_provider=explanation.get("provider") or llm_probe.get("provider"),
        model_versions={
            **(item.get("model_versions") or {}),
            "relevance": topic["model_version"],
            "claims": packed.get("model_version"),
            "risk": risk["model_version"],
            "nli": "lexical_v2_conservative",
            "llm": explanation.get("model") or "token-overlap",
            "cnn": "cnn32_64_64_dense64_v1",
        },
    )
    store.audit(
        "article",
        item["content_id"],
        "verdict",
        {"verdict": risk["verdict"], "why": risk.get("why"), "nli": nli_label},
    )
    from database.enrich import enrich_article

    enrich_article(store, item["content_id"])
    from database.thumbs import ensure_article_thumb

    ensure_article_thumb(store, store.get_article(item["content_id"]) or item)

    alert = None
    if risk["risk_score"] >= ALERT_THRESHOLD or risk["verdict"] in {"CONTRADICHO", "POSIBLEMENTE ENGAÑOSO", "REVISIÓN HUMANA"}:
        alert_id = "AL-" + hashlib.sha256(item["content_id"].encode()).hexdigest()[:12]
        alert = {
            "alert_id": alert_id,
            "content_id": item["content_id"],
            "claim_id": claims_out[0]["claim_id"] if claims_out else None,
            "risk_score": risk["risk_score"],
            "verdict": risk["verdict"],
            "explanation": risk.get("why"),
            "status": "pending_review",
            "model_name": risk["model_name"],
            "model_version": risk["model_version"],
        }
        store.insert_alert(alert)
        store.audit("alert", alert_id, "created", alert)

    return {
        "skipped": False,
        "claims": len(claims_out),
        "risk": risk,
        "alert": alert,
        "images_queued": len(imgs[:4]),
    }


def process_image_jobs(store: Store, jobs: list[dict[str, Any]]) -> tuple[int, int]:
    known = [(r["image_id"], r.get("phash") or "") for r in store.list_images()]
    processed = 0
    cnn_n = 0

    def _handle(payload: dict[str, Any]) -> Any:
        nonlocal processed, cnn_n
        result = process_image(
            payload.get("url") or "",
            alt_text=payload.get("alt_text") or "",
            content_id=payload.get("content_id") or "",
            known_phashes=known,
        )
        if not result or not result.get("ok"):
            from process import write_class_png

            fallback = IMAGES_DIR / f"fb_{hashlib.sha256((payload.get('url') or 'x').encode()).hexdigest()[:12]}.png"
            write_class_png(fallback, "PHOTOGRAPH", seed=len(known))
            result = process_image(
                str(fallback),
                alt_text=payload.get("alt_text") or "",
                content_id=payload.get("content_id") or "",
                known_phashes=known,
            )
            if result:
                result["synthetic"] = True
                result["source_url"] = payload.get("url") or result.get("source_url") or ""
        if not result or not result.get("ok"):
            store.audit("image", payload.get("url") or "unknown", "image_fail", result or {})
            return result
        store.insert_image(result)
        from database.cnn_dataset import maybe_export_cnn_sample

        sample = maybe_export_cnn_sample(store, result)
        if sample:
            cnn_n += 1
        known.append((result["image_id"], result.get("phash") or ""))
        processed += 1
        if result.get("reused"):
            article = store.get_article(result["content_id"])
            if article:
                extra_risk = int(article.get("risk_score") or 0) + 12
                store.update_article_analysis(result["content_id"], risk_score=min(100, extra_risk))
            store.audit("image", result["image_id"], "phash_reuse", {"content_id": result["content_id"]})
        return result

    drained = drain(QUEUE_IMAGE, _handle)
    pending = jobs[len(drained) :]
    for job in pending:
        _handle(job)
    return processed, cnn_n


def update_narratives(store: Store, cycle_id: str) -> dict[str, Any]:
    prev = {row["narrative_id"]: int(row.get("claim_count") or 0) for row in store.list_narratives()}
    packed = cluster_claims(store.list_claims(limit=500), previous_counts=prev)
    for cluster in packed.get("clusters") or []:
        cluster["cycle_id"] = cycle_id
        store.upsert_narrative(cluster)
    return packed


def run_cycle(
    *,
    max_sources: int = MAX_SOURCES,
    demo_seed: bool = False,
    persist: bool = True,
) -> dict[str, Any]:
    now = _now()
    cycle_id = "CYC-" + now.strftime("%Y%m%dT%H%M%SZ")
    store = Store()
    catalog = load_catalog()
    store.sync_sources(catalog)
    purged = store.purge_fake_urls()
    if purged.get("articles_deleted"):
        print(f"  [urls] eliminados {purged['articles_deleted']} artículos con hosts inválidos")
    llm_probe = probe_llm()
    llm_budget = [3] if llm_probe.get("available") else [0]
    print(f"  [llm] {llm_probe.get('status')} ({llm_probe.get('reason') or llm_probe.get('model') or 'local'})")
    runtime = []
    for source in catalog:
        row = store.get_source(source["source_id"])
        runtime.append(merge_runtime(source, row))

    due = sources_due(runtime, now=now, methods=("api", "rss"))[: max(1, max_sources)]
    scrape_due = sources_due(runtime, now=now, methods=("scrape",))[:8]
    index = DedupIndex.from_store(store)

    sources_checked = 0
    scrape_deferred = 0
    errors: list[dict[str, str]] = []
    collected: list[dict[str, Any]] = []
    skipped_dup = 0
    skipped_rel = 0
    claims_n = 0
    alerts_n = 0
    image_jobs: list[dict[str, Any]] = []

    for source in scrape_due:
        note = scrape_deferred_note(source)
        store.mark_source_result(
            source["source_id"],
            ok=True,
            error=None,
            next_check=_iso(now + timedelta(minutes=frequency_minutes(source))),
            note=note,
        )
        store.audit("source", source["source_id"], "scrape_deferred", {"note": note})
        scrape_deferred += 1
        print(f"  [scrape deferred] {source.get('source_id')} {source.get('name')}")

    for source in due:
        method = resolve_access(source)
        sources_checked += 1
        items, error = _retry_fetch(source, method)
        fails = int(source.get("consecutive_failures") or 0)
        if error:
            fails += 1
            nxt = backoff_next_check(fails, now=now)
            store.mark_source_result(source["source_id"], ok=False, error=error, next_check=_iso(nxt))
            errors.append({"source_id": source["source_id"], "error": error})
            print(f"  [error] {source.get('source_id')} {error[:120]}")
            continue
        nxt = now + timedelta(minutes=frequency_minutes(source))
        store.mark_source_result(source["source_id"], ok=True, next_check=_iso(nxt))
        store.audit("source", source["source_id"], "checked", {"method": method, "items": len(items)})
        for item in items:
            payload = item.to_dict() if hasattr(item, "to_dict") else dict(item)
            append_raw(source["source_id"], {"source": source["source_id"], "item": payload})
            text = f"{payload.get('title', '')} {payload.get('text', '')}"
            dup, reason = index.register(payload.get("url") or "", text)
            if dup:
                skipped_dup += 1
                store.audit("article", payload.get("url") or "", "dedup", {"reason": reason})
                continue
            collected.append(payload)

    if _want_demo_seed(demo_seed) and not collected:
        seeded = inject_demo_seed(store, index)
        if seeded:
            print(f"  [semilla demo] {len(seeded)} artículos (sin fetch útil)")
            collected.extend(seeded)

    if os.environ.get("TNB_IMPORT_CORPUS", "1") == "1":
        imported = inject_corpus(store, index)
        if imported:
            print(f"  [corpus Generador] {len(imported)} documentos/youtube/social")
            collected.extend(imported)

    analyzed = 0
    for payload in collected:
        source = store.get_source(payload.get("source_id") or "") or {
            "source_id": payload.get("source_id"),
            "type": payload.get("source_type"),
        }
        try:
            result = analyze_article(
                store, payload, source, image_jobs, llm_probe=llm_probe, llm_budget=llm_budget
            )
        except Exception as exc:  # noqa: BLE001
            store.audit("article", payload.get("content_id") or payload.get("url") or "", "analyze_fail", {"error": str(exc)[:200]})
            print(f"  [analyze fail] {payload.get('title', '')[:60]} {exc}")
            continue
        if result.get("skipped"):
            skipped_rel += 1
            continue
        analyzed += 1
        claims_n += int(result.get("claims") or 0)
        if result.get("alert"):
            alerts_n += 1

    if analyzed == 0 and _want_demo_seed(demo_seed):
        seeded = inject_demo_seed(store, index)
        print(f"  [semilla demo] {len(seeded)} artículos (RSS sin relevantes)")
        for payload in seeded:
            source = store.get_source(payload.get("source_id") or "") or {"source_id": payload.get("source_id")}
            result = analyze_article(store, payload, source, image_jobs, llm_probe=llm_probe, llm_budget=llm_budget)
            if result.get("skipped"):
                skipped_rel += 1
                continue
            analyzed += 1
            claims_n += int(result.get("claims") or 0)
            if result.get("alert"):
                alerts_n += 1

    images_n, cnn_samples_n = process_image_jobs(store, image_jobs)
    try:
        from database.cnn_dataset import purge_synthetic_dataset

        purge_synthetic_dataset()
    except Exception:
        pass
    narratives = update_narratives(store, cycle_id)
    from database.cnn_dataset import dataset_counts
    from database.mysql_mirror import mysql_status
    from database.mine_state import record_cycle

    mysql_info = mysql_status()
    finished = _iso(_now())
    store.insert_mining_run(
        {
            "cycle_id": cycle_id,
            "started_at": _iso(now),
            "finished_at": finished,
            "articles_new": analyzed,
            "images_new": images_n,
            "errors": len(errors),
            "extra": {
                "skipped_duplicates": skipped_dup,
                "cnn_samples_new": cnn_samples_n,
                "scrape_deferred": scrape_deferred,
            },
        }
    )

    summary = {
        "cycle_id": cycle_id,
        "ran_at": _iso(now),
        "project_root": str(PROJECT_ROOT),
        "framework_root": str(FRAMEWORK_ROOT),
        "sources_checked": sources_checked,
        "scrape_deferred": scrape_deferred,
        "articles_fetched": len(collected),
        "articles_new": analyzed,
        "skipped_duplicates": skipped_dup,
        "skipped_relevance": skipped_rel,
        "images_processed": images_n,
        "cnn_samples_new": cnn_samples_n,
        "cnn_dataset": dataset_counts(),
        "claims": claims_n,
        "alerts": alerts_n,
        "narratives": narratives.get("growth"),
        "errors": errors,
        "llm": llm_probe,
        "kpis": store.kpis(),
        "mysql": mysql_info,
        "db": str(store.path),
    }
    record_cycle(summary)
    store.audit("cycle", cycle_id, "completed", summary)
    try:
        from backup_db import backup_sqlite
        from bootstrap import DB_PATH as _PROD_DB

        if Path(store.path).resolve() == Path(_PROD_DB).resolve():
            backup_sqlite(store.path)
    except Exception as exc:  # noqa: BLE001
        print(f"  [backup] {exc}")
    _print_es(summary)
    if not persist:
        store.close()
    return summary


def _print_es(summary: dict[str, Any]) -> None:
    print()
    print("=== The NewsBreakers — ciclo ===")
    print(f"Fuentes revisadas:     {summary['sources_checked']}")
    print(f"Scrape diferido:       {summary['scrape_deferred']}")
    print(f"Artículos nuevos:      {summary['articles_new']}")
    print(f"Imágenes procesadas:   {summary['images_processed']}")
    print(f"Muestras CNN nuevas:   {summary.get('cnn_samples_new') or 0}")
    print(f"Claims:                {summary['claims']}")
    print(f"Alertas:               {summary['alerts']}")
    print(f"Duplicados omitidos:   {summary['skipped_duplicates']}")
    print(f"Irrelevantes omitidos: {summary['skipped_relevance']}")
    if summary.get("errors"):
        print(f"Errores de fuente:     {len(summary['errors'])}")
    mysql = summary.get("mysql") or {}
    print(f"MySQL:                 {'conectado' if mysql.get('connected') else 'MySQL no conectado'}")
    kpis = summary.get("kpis") or {}
    backend = kpis.get("backend") or "sqlite"
    print(
        f"Totales ({backend}):        artículos={kpis.get('articles')}  "
        f"claims={kpis.get('claims')}  alertas={kpis.get('alerts')}  imágenes={kpis.get('images')}"
    )
    ds = summary.get("cnn_dataset") or {}
    if ds:
        filled = ", ".join(f"{k}:{v}" for k, v in ds.items() if v)
        if filled:
            print(f"Dataset CNN:           {filled}")
            print("  (reentrenar: python -m ai_service.vision.train_cnn)")
    print(f"Base: {summary.get('db')}")
    print()


def next_sleep_seconds(store: Store, floor: int = 15, cap: int = 3600) -> int:
    now = _now()
    soonest = None
    for source in store.list_sources(active_only=True):
        nxt = source.get("next_check")
        if not nxt:
            continue
        try:
            dt = datetime.fromisoformat(str(nxt).replace("Z", "+00:00"))
        except ValueError:
            continue
        if soonest is None or dt < soonest:
            soonest = dt
    if soonest is None:
        return floor
    delta = int((soonest - now).total_seconds())
    return max(floor, min(cap, delta if delta > 0 else floor))


def main(argv: list[str] | None = None) -> dict[str, Any]:
    parser = argparse.ArgumentParser(description="The NewsBreakers — un ciclo del pipeline")
    parser.add_argument("--loop", action="store_true", help="Repetir según --interval o next_check")
    parser.add_argument("--interval", type=int, default=None, help="Segundos entre ciclos (ej. 1800)")
    parser.add_argument("--demo-seed", action="store_true", help="Inyectar artículos demo")
    parser.add_argument("--max-sources", type=int, default=MAX_SOURCES)
    args = parser.parse_args(argv)
    os.environ.setdefault("TNB_DEMO_ROOT", str(PROJECT_ROOT))
    from database.mine_state import mine_interval_seconds, record_cycle

    while True:
        summary = run_cycle(max_sources=args.max_sources, demo_seed=args.demo_seed)
        if not args.loop:
            return summary
        if args.interval and args.interval > 0:
            sleep_s = max(15, args.interval)
        elif os.environ.get("TNB_MINE_INTERVAL_MINUTES"):
            sleep_s = mine_interval_seconds(args.interval)
        else:
            store = Store()
            sleep_s = next_sleep_seconds(store)
        record_cycle(summary, sleep_s)
        print(f"Siguiente ciclo en {sleep_s}s…")
        time.sleep(sleep_s)


if __name__ == "__main__":
    main()
