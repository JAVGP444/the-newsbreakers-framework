"""Gateway FastAPI — sirve SQLite del pipeline (puerto 8010)."""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

FW = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(FW))

from bootstrap import CNN_DIR, CNN_WEIGHTS, DB_PATH, IMAGES_DIR, PROJECT_ROOT, ensure_paths  # noqa: E402

ensure_paths()

from database.query_filters import parse_article_query  # noqa: E402
from database.store import Store  # noqa: E402
from pipeline.run import MAX_SOURCES, run_cycle  # noqa: E402
from source_catalog import frequency_minutes, select_access_method  # noqa: E402
from workers.queues import QUEUES  # noqa: E402


def _query(
    disease: str | None = None,
    compare: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    country: str | None = None,
    verdict: str | None = None,
    source: str | None = None,
    source_id: str | None = None,
    q: str | None = None,
    origin: str | None = None,
    raw_format: str | None = None,
    stance: str | None = None,
    risk_min: int | None = None,
    risk_max: int | None = None,
    risk_null: bool = False,
    page: int = 1,
    page_size: int = 12,
    limit: int | None = None,
    order: str | None = None,
):
    return parse_article_query(
        disease=disease,
        compare=compare,
        date_from=date_from,
        date_to=date_to,
        country=country,
        verdict=verdict,
        source=source,
        source_id=source_id,
        q=q,
        origin=origin,
        raw_format=raw_format,
        stance=stance,
        risk_min=risk_min,
        risk_max=risk_max,
        risk_null=risk_null,
        page=page,
        page_size=page_size,
        limit=limit,
        order=order,
    )

app = FastAPI(
    title="The NewsBreakers",
    version="1.0.0",
    description="Pipeline multimodal salud animal. LLM no decide la verdad.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
IMAGES_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/files/images", StaticFiles(directory=str(IMAGES_DIR)), name="images")


def _api_token() -> str:
    return (os.environ.get("TNB_API_TOKEN") or "").strip()


@app.middleware("http")
async def require_api_token(request: Request, call_next):
    token = _api_token()
    if token and request.method == "POST":
        path = request.url.path.rstrip("/") or "/"
        protected = path == "/cycle" or path == "/cnn/predict" or path.endswith("/review")
        if protected:
            got = request.headers.get("X-API-Token") or request.headers.get("x-api-token") or ""
            if got != token:
                return JSONResponse(status_code=401, content={"detail": "invalid or missing X-API-Token"})
    return await call_next(request)


class ReviewIn(BaseModel):
    human_label: str
    reason: str = ""
    analyst: str = "analista"


class TranslateIn(BaseModel):
    texts: list[str] = []


def _store() -> Store:
    return Store()


def _backfill_thumb_ids(content_ids: list[str]) -> None:
    from database.thumbs import ensure_article_thumb

    store = Store()
    try:
        for cid in content_ids:
            row = store.get_article(cid)
            if row:
                ensure_article_thumb(store, row)
    finally:
        store.close()


@app.get("/health")
def health():
    store = _store()
    from database.cnn_dataset import dataset_counts
    from database.mine_state import mine_banner
    from database.mysql_mirror import mysql_status

    mysql = mysql_status()
    mine = mine_banner()
    last = store.last_mining_run() or {}
    kpis = store.kpis()
    lag = store.mysql_lag_info()
    return {
        "status": "ok",
        "service": "tnb-pipeline",
        "db": str(DB_PATH),
        "db_exists": DB_PATH.is_file(),
        "project_root": str(PROJECT_ROOT),
        "kpis": kpis,
        "mysql": bool(mysql.get("connected")),
        "mysql_error": None if mysql.get("connected") else (mysql.get("error") or "MySQL no conectado"),
        "mysql_lag_seconds": lag.get("mysql_lag_seconds"),
        "mysql_stale": lag.get("mysql_stale"),
        "last_mine": mine.get("last_mine") or last.get("started_at") or last.get("finished_at"),
        "next_mine_minutes": mine.get("next_mine_minutes"),
        "mine": mine,
        "cnn_dataset": dataset_counts(),
        "postgres": bool(os.getenv("POSTGRES_URL")),
        "mongo": bool(os.getenv("MONGO_URL")),
        "redis": bool(os.getenv("REDIS_URL")),
        "llm_does_not_decide_truth": True,
        "queues": list(QUEUES),
    }


@app.get("/sources")
def sources():
    rows = []
    for s in _store().list_sources():
        rows.append(
            {
                **s,
                "access_resolved": select_access_method(s),
                "frequency_minutes": s.get("frequency_minutes") or frequency_minutes(s),
                "healthy": s.get("healthy", not s.get("last_error")),
                "article_count": s.get("article_count", 0),
                "status": s.get("status") or ("error" if s.get("last_error") else "ok"),
            }
        )
    return {"count": len(rows), "sources": rows}


@app.get("/articles")
def articles(
    background_tasks: BackgroundTasks,
    limit: int | None = Query(default=None),
    disease: str | None = Query(default=None),
    compare: str | None = Query(default=None),
    date_from: str | None = Query(default=None, alias="from"),
    date_to: str | None = Query(default=None, alias="to"),
    country: str | None = Query(default=None),
    verdict: str | None = Query(default=None),
    source: str | None = Query(default=None),
    source_id: str | None = Query(default=None),
    q: str | None = Query(default=None),
    origin: str | None = Query(default=None),
    raw_format: str | None = Query(default=None),
    stance: str | None = Query(default=None),
    risk_min: int | None = Query(default=None),
    risk_max: int | None = Query(default=None),
    risk_null: bool = Query(default=False),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=12, ge=1, le=400),
    order: str | None = Query(default=None),
    thumb_page: int = Query(default=1, ge=1),
    thumb_limit: int = Query(default=12, ge=0, le=80),
    backfill_all: bool = Query(default=False),
):
    store = _store()
    query = _query(
        disease=disease,
        compare=compare,
        date_from=date_from,
        date_to=date_to,
        country=country,
        verdict=verdict,
        source=source,
        source_id=source_id,
        q=q,
        origin=origin,
        raw_format=raw_format,
        stance=stance,
        risk_min=risk_min,
        risk_max=risk_max,
        risk_null=risk_null,
        page=page,
        page_size=page_size if limit is None else limit,
        limit=limit,
        order=order,
    )
    payload = store.paged_articles(query)
    rows = payload["articles"]
    if thumb_limit > 0:
        batch = rows if backfill_all else rows[:thumb_limit]
        ids = [str(r.get("content_id") or "") for r in batch if r.get("content_id")]
        if ids:
            background_tasks.add_task(_backfill_thumb_ids, ids)
    out = []
    for row in rows:
        fresh = store.public_row(row) or row
        fresh["disease_list"] = store.article_diseases(fresh)
        out.append(fresh)
    return {
        "count": payload["count"],
        "page": payload["page"],
        "page_size": payload["page_size"],
        "articles": out,
    }


@app.get("/thumbs/{content_id}")
def serve_thumb(content_id: str):
    store = _store()
    row = store.resolve_article(content_id)
    if not row:
        raise HTTPException(404, "article not found")
    from database.thumbs import ensure_article_thumb, is_generic_visual

    path = ensure_article_thumb(store, row)
    if path is None or not Path(path).is_file() or is_generic_visual(str(path)):
        raise HTTPException(404, "thumb not found")
    return FileResponse(path, media_type="image/jpeg", filename=Path(path).name)


@app.get("/articles/{content_id}")
def article_detail(content_id: str):
    store = _store()
    row = store.resolve_article(content_id)
    if not row:
        return JSONResponse(
            status_code=404,
            content={
                "detail": "article not found",
                "content_id": content_id,
                "recent": store.recent_article_cards(5),
            },
        )
    content_id = row["content_id"]
    from database.enrich import article_timeline, compact_graph, enrich_article, filter_article_evidence, similar_or_related

    enrich_article(store, content_id)
    row = store.get_article(content_id) or row
    claims = store.list_claims(content_id)
    evidence = []
    for claim in claims:
        evidence.extend(store.list_evidence(claim["claim_id"]))
    evidence = filter_article_evidence(row, evidence, store)
    from database.thumbs import ensure_article_thumb

    ensure_article_thumb(store, row)
    row = store.get_article(content_id) or row
    images = store.list_images(content_id)
    quality = store.explanation_quality(row, claims, evidence, images)
    local_text = store.local_explanation(row, claims, evidence)
    from database.geo import country_info, resolve_article_country

    extra = " ".join((c.get("location") or "") for c in claims)
    geo = country_info(resolve_article_country(row, extra))
    timeline = article_timeline(row)
    row = dict(store.public_row(row) or row)
    row["disease_list"] = store.article_diseases(row)
    row["local_explanation"] = local_text
    row["summary"] = (row.get("text") or "")[:420]
    row["explanation_quality"] = quality
    evidence = [store.public_row(e) or e for e in evidence]
    similar = similar_or_related(store, content_id, limit=5)
    return {
        "article": row,
        "source": store.get_source(row.get("source_id") or ""),
        "claims": claims,
        "evidence": evidence,
        "images": images,
        "entities": store.fetchall("SELECT * FROM entities WHERE content_id=?", (content_id,)),
        "entities_grouped": store.grouped_entities(content_id),
        "geo": geo,
        "timeline": timeline,
        "similar": similar,
        "graph": compact_graph(row, similar, store),
        "quality": quality,
        "audit": store.list_audit(content_id, limit=50),
        "alerts": [a for a in store.list_alerts() if a.get("content_id") == content_id],
    }


@app.get("/claims")
def claims(limit: int = 200):
    return {"count": _store().count_claims(), "claims": _store().list_claims(limit=limit)}


@app.get("/alerts")
def alerts(
    status: str | None = Query(default=None),
    include: str | None = Query(default="article,claims,evidence"),
):
    store = _store()
    want = bool(include)
    rows = store.list_alerts(limit=200, status=status, include=want)
    if not want:
        for row in rows:
            art = store.get_article(row.get("content_id") or "")
            row["title"] = (art or {}).get("title") or row.get("content_id")
            row["article_verdict"] = (art or {}).get("verdict")
    return {
        "count": store.count_alerts(),
        "pending": store.count_alerts("pending_review"),
        "alerts": rows,
    }


@app.get("/images")
def images(disease: str | None = Query(default=None)):
    store = _store()
    rows = store.list_images()
    if disease:
        allowed = {a["content_id"] for a in store.filtered_articles(disease)}
        rows = [r for r in rows if r.get("content_id") in allowed]
    return {"images": rows}


@app.get("/images/{image_id}")
def serve_image(image_id: str):
    store = _store()
    row = None
    if image_id.isdigit():
        imgs = store.list_images()
        idx = int(image_id)
        if 1 <= idx <= len(imgs):
            row = imgs[idx - 1]
        elif imgs:
            row = imgs[0]
    if row is None:
        row = store.get_image(image_id)
    path = None
    mime = "image/png"
    if row:
        mime = row.get("mime_type") or mime
        raw = Path(str(row.get("storage_key") or ""))
        if raw.is_file():
            path = raw
        else:
            candidate = IMAGES_DIR / raw.name
            if candidate.is_file():
                path = candidate
    if path is None:
        direct = IMAGES_DIR / image_id
        if direct.is_file():
            path = direct
        else:
            matches = list(IMAGES_DIR.glob(f"{image_id}*"))
            path = matches[0] if matches else None
    if path is None or not path.is_file():
        raise HTTPException(404, "image not found")
    suffix = path.suffix.lower()
    mime_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".svg": "image/svg+xml",
    }
    return FileResponse(path, media_type=mime_map.get(suffix, mime), filename=path.name)


@app.get("/narratives")
def narratives():
    return {"narratives": _store().list_narratives()}


@app.get("/kpis")
def kpis():
    return _store().kpis()


def _common_query(
    disease: str | None = None,
    compare: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    country: str | None = None,
    verdict: str | None = None,
    source: str | None = None,
    q: str | None = None,
    raw_format: str | None = None,
    stance: str | None = None,
    origin: str | None = None,
    risk_min: int | None = None,
    risk_max: int | None = None,
    risk_null: bool = False,
):
    return _query(
        disease=disease,
        compare=compare,
        date_from=date_from,
        date_to=date_to,
        country=country,
        verdict=verdict,
        source=source,
        q=q,
        origin=origin,
        raw_format=raw_format,
        stance=stance,
        risk_min=risk_min,
        risk_max=risk_max,
        risk_null=risk_null,
    )


@app.get("/stats")
def stats(
    disease: str | None = Query(default=None),
    compare: str | None = Query(default=None),
    date_from: str | None = Query(default=None, alias="from"),
    date_to: str | None = Query(default=None, alias="to"),
    country: str | None = Query(default=None),
    verdict: str | None = Query(default=None),
    source: str | None = Query(default=None),
    q: str | None = Query(default=None),
    origin: str | None = Query(default=None),
    raw_format: str | None = Query(default=None),
    stance: str | None = Query(default=None),
):
    from database.cnn_dataset import dataset_counts
    from database.mine_state import mine_banner

    query = _common_query(disease, compare, date_from, date_to, country, verdict, source, q, raw_format, stance, origin)
    payload = _store().stats_payload(disease, q=query)
    payload["mine"] = mine_banner()
    payload["cnn_dataset"] = dataset_counts()
    return payload


@app.get("/charts")
def charts(
    disease: str | None = Query(default=None),
    compare: str | None = Query(default=None),
    date_from: str | None = Query(default=None, alias="from"),
    date_to: str | None = Query(default=None, alias="to"),
    country: str | None = Query(default=None),
    verdict: str | None = Query(default=None),
    source: str | None = Query(default=None),
    q: str | None = Query(default=None),
    origin: str | None = Query(default=None),
    raw_format: str | None = Query(default=None),
    stance: str | None = Query(default=None),
    risk_min: int | None = Query(default=None),
    risk_max: int | None = Query(default=None),
    risk_null: bool = Query(default=False),
):
    query = _query(
        disease=disease,
        compare=compare,
        date_from=date_from,
        date_to=date_to,
        country=country,
        verdict=verdict,
        source=source,
        q=q,
        origin=origin,
        raw_format=raw_format,
        stance=stance,
        risk_min=risk_min,
        risk_max=risk_max,
        risk_null=risk_null,
    )
    return _store().chart_payload(disease, q=query)


@app.get("/graph")
def graph(
    disease: str | None = Query(default=None),
    compare: str | None = Query(default=None),
    date_from: str | None = Query(default=None, alias="from"),
    date_to: str | None = Query(default=None, alias="to"),
    country: str | None = Query(default=None),
    verdict: str | None = Query(default=None),
    source: str | None = Query(default=None),
    q: str | None = Query(default=None),
    origin: str | None = Query(default=None),
    raw_format: str | None = Query(default=None),
    limit: int = Query(default=40, ge=10, le=80),
):
    query = _common_query(disease, compare, date_from, date_to, country, verdict, source, q, raw_format, origin=origin)
    return _store().network_graph(disease, q=query, limit=limit)


@app.get("/diseases")
def diseases():
    return {"diseases": _store().disease_counts()}


@app.get("/geo")
def geo(
    disease: str | None = Query(default=None),
    compare: str | None = Query(default=None),
    date_from: str | None = Query(default=None, alias="from"),
    date_to: str | None = Query(default=None, alias="to"),
    country: str | None = Query(default=None),
    verdict: str | None = Query(default=None),
    source: str | None = Query(default=None),
    q: str | None = Query(default=None),
    origin: str | None = Query(default=None),
    raw_format: str | None = Query(default=None),
    level: str = Query(default="country"),
):
    query = _common_query(disease, compare, date_from, date_to, country, verdict, source, q, raw_format, origin=origin)
    countries = _store().geo_table(disease, q=query)
    located = [c for c in countries if not c.get("unlocated")]
    unlocated = [c for c in countries if c.get("unlocated")]
    return {
        "level": level,
        "countries": countries,
        "unlocated": unlocated,
        "points": [
            {
                "country": c["country"],
                "name": c["name"],
                "lat": c.get("lat"),
                "lng": c.get("lng"),
                "count": c["count"],
                "articles": c.get("articles") or [],
                "unlocated": bool(c.get("unlocated")),
            }
            for c in located
        ],
    }


@app.get("/youtube")
def youtube():
    return {"videos": _store().list_by_format("youtube")}


@app.get("/social")
def social():
    return {"signals": _store().list_by_format("social")}


@app.get("/status")
def status():
    from bootstrap import CNN_WEIGHTS
    from llm import probe_llm

    probe = probe_llm()
    return {
        "llm": probe,
        "cnn": {
            "weights": str(CNN_WEIGHTS),
            "weights_exist": CNN_WEIGHTS.is_file(),
            "model_version": "cnn32_64_64_dense64_v1",
            "architecture": "Conv2D32-Pool-Conv2D64-Pool-Conv2D64-Flatten-Dense64-Dense8",
            "role": "academic_experimental",
            "production_encoder": "clip_or_resnet18_imagenet",
        },
        "ocr": {"engines": ["pytesseract", "paddleocr", "document_intelligence_studio", "alt_text"]},
        "kpis": _store().kpis(),
        "llm_does_not_decide_truth": True,
    }


@app.post("/translate")
def translate(payload: TranslateIn):
    from api.translate import translate_texts

    texts = payload.texts or []
    return {"texts": translate_texts(texts)}


@app.post("/alerts/{alert_id}/review")
def review_alert(alert_id: str, payload: ReviewIn):
    row = _store().review_alert(
        alert_id,
        human_label=payload.human_label,
        reason=payload.reason,
        analyst=payload.analyst,
    )
    if not row:
        raise HTTPException(404, "alert not found")
    return {"ok": True, "alert": row}


@app.post("/cycle")
def cycle(
    max_sources: int | None = Query(default=None, ge=0, le=500),
    demo_seed: bool = False,
    force_due: bool = False,
):
    n = MAX_SOURCES if max_sources is None else max_sources
    return run_cycle(max_sources=n, demo_seed=demo_seed, force_due=force_due)


def _cnn_json(name: str, default: Any = None):
    path = CNN_DIR / name
    if not path.is_file():
        return default if default is not None else {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default if default is not None else {}


@app.get("/cnn/metrics")
def cnn_metrics():
    from cnn import ARCHITECTURE, CLASS_LABELS_ES, IMAGE_CLASSES, MODEL_VERSION
    from database.cnn_dataset import dataset_counts

    history = _cnn_json("history.json", {"acc": [], "val_acc": [], "loss": [], "val_loss": []})
    cm = _cnn_json("confusion_matrix.json", {"labels": list(IMAGE_CLASSES), "matrix": []})
    test = _cnn_json("test_metrics.json", {"test_accuracy": None})
    ds = dataset_counts()
    experimental = bool(test.get("experimental_on_synthetic", True))
    return {
        "model_version": MODEL_VERSION,
        "weights_exist": CNN_WEIGHTS.is_file(),
        "weights": str(CNN_WEIGHTS),
        "architecture": ARCHITECTURE,
        "optimizer": "Adam",
        "loss": "sparse_categorical_crossentropy",
        "metrics": ["accuracy"],
        "split": [0.7, 0.15, 0.15],
        "classes": [{"id": c, "label": CLASS_LABELS_ES.get(c, c), "index": i} for i, c in enumerate(IMAGE_CLASSES)],
        "history": history,
        "confusion_matrix": cm,
        "test_metrics": test,
        "test_accuracy": None if experimental else test.get("test_accuracy"),
        "academic_test_accuracy": test.get("test_accuracy"),
        "experimental_on_synthetic": experimental,
        "production_encoder": "open-clip ViT-B-32 o torchvision ResNet18 ImageNet",
        "production_metric": False if experimental else True,
        "samples": [],
        "samples_url": "/cnn/samples?real=1",
        "dataset": ds,
        "dataset_total": sum(ds.values()),
        "retrain": "python -m ai_service.vision.train_cnn",
        "note": (
            "Modelo productivo: CLIP/ResNet (tipo de imagen). "
            "La CNN 8 clases es laboratorio académico"
            + (" sobre dibujos sintéticos — su % no es métrica de producción." if experimental else ".")
        ),
    }


@app.get("/cnn/samples")
def cnn_sample_list(real: int = Query(default=1), limit: int = Query(default=12, ge=1, le=24)):
    """Fotos reales del observatorio (YouTube / og:image). Nunca dibujos del dataset CNN."""
    from database.thumbs import list_real_photo_samples

    samples = list_real_photo_samples(_store(), limit=limit) if real else []
    return {
        "real": True,
        "count": len(samples),
        "samples": samples,
        "empty_message": "Aún no hay fotos minadas; sube una captura de noticia o un meme real",
    }


@app.get("/cnn/samples/{name}")
def cnn_sample(name: str):
    from database.thumbs import resolve_real_sample

    path, _url, _art = resolve_real_sample(_store(), name)
    if path is None or not path.is_file():
        raise HTTPException(404, "sample not found")
    suffix = path.suffix.lower()
    mime = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}.get(
        suffix, "image/jpeg"
    )
    return FileResponse(path, media_type=mime, filename=path.name)


def _predict_path(path: str, url: str = "") -> dict:
    from image_hash import perceptual_hash
    from ocr import ocr_image
    from visual_encoder import classify_visual

    hashed = perceptual_hash(path)
    ocr = ocr_image(path, alt_text="")
    ocr_text = ocr.get("text") or ""
    vision = classify_visual(path, url=url, ocr_text=ocr_text)
    return {
        "class": vision.get("class"),
        "class_index": vision.get("class_index"),
        "label_es": vision.get("label_es"),
        "confidence": vision.get("confidence"),
        "scores": vision.get("scores"),
        "weights_loaded": vision.get("weights_loaded"),
        "model_version": vision.get("model_version"),
        "encoder": vision.get("encoder"),
        "role": vision.get("role"),
        "note": vision.get("note"),
        "phash": hashed.get("phash"),
        "phash_short": (hashed.get("phash") or "")[:8],
        "phash_bits": hashed.get("bits"),
        "ocr_text": ocr_text[:800],
        "ocr_engine": ocr.get("engine") or ocr.get("model_version"),
        "width": vision.get("width"),
        "height": vision.get("height"),
        "animal_health_relevance": vision.get("animal_health_relevance"),
        "academic": vision.get("academic"),
        "production": vision.get("production"),
        "visual_fusion": {
            "type": vision.get("class"),
            "encoder": vision.get("encoder"),
            "ocr_text": ocr_text[:400],
            "animal_health_relevance": vision.get("animal_health_relevance"),
        },
    }


@app.post("/cnn/predict")
async def cnn_predict(
    file: UploadFile | None = File(default=None),
    sample_id: str | None = Form(default=None),
):
    path = None
    tmp = None
    page_url = ""
    if sample_id:
        from database.thumbs import resolve_real_sample

        resolved, page_url, _art = resolve_real_sample(_store(), sample_id)
        if resolved is None or not resolved.is_file():
            raise HTTPException(404, "sample not found")
        path = str(resolved)
    elif file is not None:
        suffix = Path(file.filename or "upload.png").suffix.lower() or ".png"
        if suffix not in {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}:
            suffix = ".png"
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        tmp.write(await file.read())
        tmp.close()
        path = tmp.name
    else:
        raise HTTPException(400, "file or sample_id required")
    try:
        return _predict_path(path, url=page_url)
    finally:
        if tmp is not None:
            try:
                Path(tmp.name).unlink(missing_ok=True)
            except Exception:
                pass


def _load_env() -> None:
    path = FW / ".env"
    if not path.is_file():
        return
    try:
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
    except OSError:
        return


_load_env()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host=os.environ.get("GATEWAY_HOST", "127.0.0.1"),
        port=int(os.environ.get("GATEWAY_PORT") or 8010),
    )

