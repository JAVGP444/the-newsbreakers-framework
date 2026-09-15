# Auditoría del framework — The NewsBreakers

> **Español / English.** Auditoría interna (septiembre 2026). No es la guía de instalación. Instalación actual: [`README.md`](../README.md) y `docs/install-es.pdf` / `docs/install-en.pdf`.
>
> **English.** Internal audit (September 2026). Not the install guide. Current install: [`README.md`](../README.md) and the install PDFs.

**Fecha:** 10 de septiembre de 2026  
**Ámbito:** `C:\Users\javie\OneDrive\Escritorio\the-newsbreakers-framework`  
**Origen relacionado:** `C:\Users\javie\OneDrive\Escritorio\Generador_Excel_Enfermedades`  
**No es objeto de esta auditoría como producto:** el verificador FastAPI+Next.js en `the-newsbreakers` (puertos 8000/3003). Se reutilizan piezas (`claim_extractor`, `ai_verifier`) vía `PYTHONPATH`.

**Veredicto global:** el framework es un **MVP ejecutable y demostrable**, no un sistema de vigilancia 24/7 de producción. El embudo (watchlist → ciclo → SQLite → dashboard Vite) existe de punta a punta. La mayoría de las capas “inteligentes” son **heurísticas léxicas** con contratos de arquitectura listos; embeddings, scrape, NLI neuronal, CLIP, HITL en UI, backups y servicio Windows están **en stub o ausentes**.

Leyenda de madurez:

| Etiqueta | Significado |
|----------|-------------|
| **Producción-local** | Sirve para demo y operación en un PC, con límites conocidos |
| **MVP** | Funciona de punta a punta; no aguanta volumen, calidad ni fallos reales |
| **Stub** | Contrato / función / tabla; no hace el trabajo del plan maestro |

---

## 1. Alcance: arquitectura vs plan maestro

El plan (docs del framework + bases del PDF de vigilancia) pide:

> Watchlist → ingesta (RSS/API/scrape) → NLP → CNN/OCR → evidencia primero → narrativas → riesgo → HITL → 24/7 → MySQL → dashboard (sala, mapa, gráficas, grafo, fichas).

Lo que hay **hoy**:

```
Watchlist YAML (~109 fuentes, ~8 RSS reales, 1 API GDELT, ~100 scrape diferido)
        │
   scheduler de un proceso (run_cycle / mine_loop)
        │
   RSS + GDELT (título/summary, no cuerpo completo)
        │
   Dedup URL + SHA texto  (semántica = False)
        │
   Keywords + gazetteer + regex de claims
        │
   Evidencia = fichas YAML / homes oficiales  (NLI léxico)
        │
   Risk ponderado  →  alertas pending_review  (API HITL sí, UI no)
        │
   SQLite tnb.db  (+ dual-write MySQL si Docker está)
        │
   Dashboard Vite :5173  (sala / mapa / gráficas / grafo / CNN / ficha)
```

| Capacidad del plan | Estado real |
|--------------------|-------------|
| Watchlist (no crawler abierto) | **MVP sólido** — catálogo + `scrape deferred` |
| Ingesta RSS/API | **MVP** — GDELT y RSS cortos; scrape no implementado |
| NLP / claims / entidades | **MVP léxico** — gazetteer del Generador, no spaCy/transformers |
| CNN académica 8 clases | **MVP académico sobre sintético** — pesos existen; no generaliza a fotos reales |
| OCR | **Stub con fallback** — PaddleOCR opcional; por defecto alt-text |
| pHash | **MVP aHash 8×8** — no pHash DCT ni CLIP |
| Evidence-first / NLI | **MVP léxico** — el LLM no cierra la verdad (bien); el NLI es overlap de tokens |
| Narrativas / embeddings | **Stub/MVP keywords** — 4 clusters fijos; vectores = ceros |
| Risk + alertas | **MVP** — fórmula y veredictos correctos (no FAKE/REAL) |
| HITL | **API MVP / UI stub** |
| 24/7 | **Bucle Python** — no servicio Windows, no Celery, Docker incompleto |
| MySQL | **Dual-write MVP** — warehouse si está arriba; SQLite es la fuente de lectura |
| Dashboard | **MVP UI rico** — falta cola HITL, auth, narrativas como panel propio |

**Tres productos en el escritorio (no mezclar):**

| Carpeta | Rol | UI |
|---------|-----|----|
| `Generador_Excel_Enfermedades` | Origen: Excel, DuckDB, `source_registry.yaml`, diccionarios, HTML offline | `salida/urls_enfermedades_dashboard.html` |
| `the-newsbreakers-framework` | Pipeline 24/7 + observatorio Vite | `http://127.0.0.1:5173` |
| `the-newsbreakers` | Verificador reactivo (legado) | Next.js :3003 — **no** es fuente de verdad |

---

## 2. Áreas (estado · hueco · cómo implementarlo)

### 2.1 Ingesta (RSS / API / scrape, scheduler, retries, robots)

**Estado actual — MVP**

- Catálogo: `ingestion/sources/catalog.yaml` (~**109** fuentes, generado desde el Generador).
- Overrides RSS: `ingestion/sources/rss_overrides.yaml` (WHO, WOAH, CDC, CIDRAP, Poultry World, etc.).
- Tras fusionar overrides: ~**8** `rss_url` reales, **1** API (GDELT), ~**100** `access_method: scrape`.
- Ciclo: `pipeline/run.py` → `sources_due(..., methods=("api","rss"))`. Scrape solo escribe log `scrape deferred`.
- RSS: `ingestion/rss_fetcher.py` (httpx + ElementTree; título, link, summary, enclosures). **No baja el HTML del artículo.**
- API: `ingestion/api_fetcher.py` — GDELT DOC 2.0, query fija H5N1/screwworm/etc. El “texto” es `seendate` + dominio, **no el cuerpo**.
- Retries: 3 intentos, backoff 30s/2m (o 2s/5s si `TNB_FAST=1`, **que es el default**).
- Cortesía: `ingestion/access.py` delays por prioridad. `robots_allowed()` existe (**fail-closed**) y **nadie la llama**.
- Scheduler: `ingestion/scheduler.py` es un wrapper de `run_cycle`. Frecuencias 15/30/60/360/720 min en catálogo.
- Colas: `workers/queues.py` — Redis opcional; si no, `queue.Queue`. El NLP **no** corre en worker: el ciclo analiza en el mismo proceso. Solo la cola de imagen se drena.

**Hueco**

- El 90 % de la watchlist no se recolecta nunca.
- Sin cuerpo de artículo no hay claims de calidad (RSS trae 1–2 frases).
- GDELT no usa GKG ni Events (el PDF de bases sí los pide).
- No hay scrape HTML (newspaper3k / trafilatura / selectores por `parser_version`).
- `robots.txt` muerto. Sin rate-limit persistente ni circuit breaker por dominio.
- `TNB_MAX_SOURCES` default 12: ni siquiera recorre todos los RSS cada ciclo.
- Dockerfile del gateway no copia `pipeline/` ni `database/` completos para un ciclo real.

**Cómo implementarlo**

| Paso | Archivos / libs | Esfuerzo |
|------|-----------------|----------|
| Auditar RSS reales por dominio (WOAH, WHO, FAO, SENASICA, PAHO, USDA) | `rss_overrides.yaml`, `_generate_catalog.py` | 1–2 días |
| Fetch de cuerpo: `trafilatura` o `readability-lxml` tras RSS, solo allowlist | nuevo `ingestion/html_fetcher.py`; llamar `robots_allowed` | 3–4 días |
| GDELT: query por enfermedad desde `diseases.yaml`; guardar JSON RAW | `api_fetcher.py`; `data/raw/*.jsonl` ya existe | 1 día |
| Scrape diferido → cola con parser por `source_id` (solo 5 oficiales primero) | `access.py`, parsers en `ingestion/parsers/` | 1 semana |
| Default `TNB_FAST=0` en minería | `pipeline/run.py` línea `RETRY_FAST` | 30 min |
| Tests de RSS vivos (skip si red cae) | `tests/test_ingestion.py` | 0.5 día |

---

### 2.2 Persistencia (SQLite vs MySQL, backups, schema)

**Estado actual — MVP (SQLite producción-local; MySQL dual-write incompleto)**

- SQLite: `data/processed/tnb.db` — `database/store.py`. Tablas: sources, articles, images, claims, evidence, alerts, reviews, audit_logs, narratives, entities, mining_runs, cnn_samples. WAL activado. Migraciones `ALTER TABLE` ad hoc.
- RAW: JSONL en `data/raw/` (`append_raw`). Mongo documentado, **no hay cliente**.
- MySQL 8: `docker-compose.yml` servicio `mysql`, schema `database/mysql/schema.sql`. Dual-write en `database/mysql_mirror.py` (reconnect 60s, backfill si warehouse vacío).
- La API **lee SQLite**, no MySQL. KPIs pueden mostrar conteos MySQL si está conectado.
- Postgres+pgvector y Redis están en compose **opcionales**; el código de runtime no escribe Postgres.

**Hueco**

- MySQL **no** tiene `reviews`, `audit_logs`, `embeddings`. HITL y trazabilidad no salen del SQLite.
- `UNIQUE (url)` en SQLite: URLs vacías (artículos in-app) pueden chocar.
- Cero backups (`sqlite3 .backup`, `mysqldump`, rotación). La DB vive en OneDrive (`tnb.db` gitignored).
- Dual-write no es transaccional: MySQL puede quedar atrás sin replay queue.
- Schema Postgres más rico que el que se usa (FKs, `narrative_claims`, `model_versions`, pgvector). Divergencia peligrosa.
- Sin retención / purga de RAW JSONL.

**Cómo implementarlo**

| Paso | Archivos / libs | Esfuerzo |
|------|-----------------|----------|
| Añadir `reviews` + `audit_logs` a MySQL y mirror | `schema.sql`, `mysql_mirror.py`, `store.insert_review` / `audit` | 1 día |
| Backup: script `tools/backup_db.ps1` (copia WAL checkpoint + zip diario) | nuevo script; Task Scheduler | 0.5 día |
| Lectura: flag `TNB_READ_MYSQL=1` o mantener SQLite como primario documentado | `store.py` / `api/main.py` | 2 días si se cambia |
| UNIQUE url: permitir NULL, no `""` | `normalize.py` + migración | 0.5 día |
| No migrar a Postgres hasta que MySQL warehouse sea estable | — | diferir |

---

### 2.3 Dedup (URL, hash de texto, semántica)

**Estado actual — MVP (capas 1–3); semántica stub**

- `ingestion/dedup.py`: URL exacta → `sha256(url)` → `sha256(texto normalizado)`.
- `semantic_similar()` **siempre False**.
- Embeddings: `ai-service/embeddings/__init__.py` devuelve ceros `implemented: False`. Worker de embedding usa 24 bytes de SHA-256 como “vector”.

**Hueco**

- No detecta republicaciones (mismo hecho, URL distinta, texto parafraseado).
- GDELT + RSS del mismo medio duplican si el summary cambia un carácter.
- pgvector documentado y no cableado.

**Cómo implementarlo**

| Paso | Archivos / libs | Esfuerzo |
|------|-----------------|----------|
| Near-dup barato: SimHash o MinHash sobre texto | `dedup.py`; `datasketch` | 1–2 días |
| Semántica: `sentence-transformers` (paraphrase-multilingual-MiniLM) + cosine 0.92 | `ai-service/embeddings`; tabla `article_embeddings` en SQLite BLOB o MySQL JSON | 3–4 días |
| pgvector solo si el volumen supera ~50k artículos | `database/postgres/schema.sql` ya listo | semana 4+ |

---

### 2.4 NLP / claims / entidades / relevancia

**Estado actual — MVP léxico (no ML)**

- Relevancia: `ai-service/nlp/relevance.py` — keywords de `diseases.yaml` + `enfermedades_config.yaml`. Umbral 0.15. Score = `min(1, hits/3)`.
- Entidades: `entities.py` gazetteer (enfermedades, especies, países, orgs). Si hay enfermedad y no hay org, **inyecta WOAH y FAO** (sesgo).
- Claims: `claims.py` regex + puente a `newsbreakers.analysis.claim_engine` y `claim_extractor` del repo legado.
- Idioma: `langdetect` (en requirements).
- Clasificador de narrativa: `classification.py` — `narrative_type: unclassified` siempre.

**Hueco**

- Nivel 3 del embudo (“clasificador ML”) no existe.
- NER no contextual (substring: “who” vs WHO).
- Claims no son tripletas estables; `verifiable` es heurístico.
- Solo 3 enfermedades en pills del dashboard; el PDF pide más (rabia, EEB, PPA, emergentes).
- `makes_false_transmission_claim` depende de regex de conspiración, no de un modelo.

**Cómo implementarlo**

| Paso | Archivos / libs | Esfuerzo |
|------|-----------------|----------|
| Relevancia: TF-IDF o logistic sobre corpus Generador (etiquetas Excel) | `classification.py`; sklearn | 3 días |
| NER: spaCy `es_core_news_md` + gazetteer como override | `entities.py` | 2–3 días |
| Claims: LLM solo para extraer estructura (ya hay `llm_extract_claims`); NLI aparte | `claims.py` + `llm.py` | 2 días |
| Ampliar diccionario a enfermedades del PDF | YAML Generador + pills en `Observatory.tsx` | 1 día |

---

### 2.5 LLM (Ollama, evidence-first)

**Estado actual — MVP de contrato (bien diseñado, poco usado)**

- `ai-service/verification/llm.py`: Ollama / OpenAI / Anthropic. Prompt: “nunca declares verdadera o falsa”. Fallback overlap local.
- `probe_llm()` alimenta el dashboard (`LLM: no disponible`).
- Presupuesto: **3 llamadas por ciclo** si Ollama responde.
- El veredicto de producto lo pone `nli.py` + `risk_engine.py`, no el LLM. Esto cumple el principio.

**Hueco**

- Anthropic está en `_resolve_provider` pero `_chat` no llama Anthropic.
- Carga `.env` del API legado (`the-newsbreakers/api/.env`) — riesgo de secretos cruzados.
- Sin cache de explicaciones; sin timeout de cola; 90s por chat puede congelar el ciclo.
- No hay evaluación (¿el summary contradice el NLI?).

**Cómo implementarlo**

| Paso | Archivos / libs | Esfuerzo |
|------|-----------------|----------|
| LLM **después** de NLI, solo explicación; nunca en el path de `verdict` | ya casi así; quitar `ai_verdict` de cualquier merge | 0.5 día |
| Cache SQLite `llm_cache(claim_hash, evidence_hash)` | `llm.py` + tabla | 1 día |
| Documentar `OLLAMA_MODEL` en `.env.example` | `.env.example` | 30 min |
| Tests: con Ollama caído el ciclo termina y el veredicto no cambia | `tests/test_pipeline.py` | 0.5 día |

---

### 2.6 Visión (CNN académica, OCR, pHash, CLIP)

**Estado actual — MVP académico / stub de producción**

- CNN PyTorch 64×64, 8 clases visuales (no FAKE/REAL): `ai-service/vision/cnn.py`. Pesos en `models/cnn/vision_cnn_v1.pt`.
- Entrenamiento: `train_cnn.py` — **dataset sintético PIL** (80/clase, 12 epochs). `test_accuracy: 0.9896` sobre el mismo tipo de dibujo. Eso **no** es accuracy en fotos de prensa.
- Export de muestras reales: `database/cnn_dataset.py` si `cnn_confidence ≥ 0.5`. Una red no entrenada produce softmax uniforme o sesgada: el umbral 0.5 **no garantiza calidad**.
- OCR: PaddleOCR si está; si no, alt RSS (`ocr_uninstalled`). Puente opcional a “WEB analizado vs code”.
- Hash: average-hash 8×8 (`image_hash.py`). Hamming ≤ 10 → reuse. No es pHash perceptual de `imagehash`.
- CLIP: **no existe**.
- Lab UI: `frontend/src/CnnLab.tsx` + `POST /cnn/predict`.
- Placeholders: si la descarga falla, se genera un PNG sintético y se clasifica igual (`process_image_jobs` fallback). Contamina el dataset.

**Hueco**

- CNN no sirve para vigilancia real hasta tener cientos de fotos humanas por clase.
- OCR no corre en el camino feliz de Windows.
- Sin CLIP no hay “esta imagen ya circuló en otro brote” multimodal.
- Fallback sintético debería **no** exportarse al dataset CNN.

**Cómo implementarlo**

| Paso | Archivos / libs | Esfuerzo |
|------|-----------------|----------|
| Prohibir export CNN de `demo_seed_*` / `fb_*` / sintéticos | `cnn_dataset.py` | 1 h |
| Dataset real: 50+ fotos/clase etiquetadas a mano (HITL) | `models/cnn/dataset/{clase}/` | 1 semana (humano) |
| Reentrenar y bajar `TNB_CNN_DATASET_MIN_CONF` a 0.8 | `train_cnn.py` | 0.5 día |
| OCR: EasyOCR (más fácil en Windows que Paddle) | `ocr.py`; `easyocr` | 1–2 días |
| pHash real: `imagehash.phash` 16×16 | `image_hash.py` | 0.5 día |
| CLIP (open-clip `ViT-B-32`) para reuse semántico | nuevo `vision/clip_embed.py` | 3–4 días |

---

### 2.7 Evidence / NLI / fuentes oficiales

**Estado actual — MVP léxico (el mayor riesgo de calidad)**

- `evidence-service/retrieve.py`: pool = fichas de `diseases.yaml` + fuentes oficiales del catálogo + `DISEASE_EVIDENCE` en `database/enrich.py`.
- URLs: WOAH disease pages (bien), SENASICA home, CDC bird-flu, **`https://www.fao.org/animal-health/en`** (históricamente 404 / rediseño FAO), USDA home.
- NLI: `nli.py` — overlap de tokens ≥ 3 ⇒ **Supported**; misinfo keywords vs snippet “oficial” ⇒ Contradicted. Fácil **falso Supported** (“brote” + “H5N1” en la ficha WOAH).
- No hay búsqueda web en vivo (a diferencia del verificador legado `web_verifier.py`).
- `public_http_url` recorta evidencia a allowlist (correcto).

**Hueco**

- No se consulta WAHIS, FAO EMPRES-i, DON de OMS, ni PDF oficiales.
- Stance no es NLI (no hay modelo entailment).
- Homes genéricos WOAH/FAO se usan como “evidencia” del claim concreto.

**Cómo implementarlo**

| Paso | Archivos / libs | Esfuerzo |
|------|-----------------|----------|
| Sustituir FAO 404 por URL viva (p. ej. `https://www.fao.org/animal-health/en/` verificar 200, o página EMPRES) | `enrich.py`, `catalog.yaml`, seed en `run.py` | 0.5 día |
| Retrieval: bajar 3 páginas oficiales por enfermedad (cache 24 h) y snippet real | `retrieve.py` + httpx + trafilatura | 2–3 días |
| NLI: `cross-encoder/nli-deberta-v3-small` o XLM-R NLI; umbral Unknown amplio | `nli.py` | 2–3 días |
| Si no hay snippet con overlap semántico → Unknown obligatorio (ya casi) | endurecer `len(overlap) >= 3` | 1 h |
| No copiar el scraper masivo del verificador; sí reutilizar `trusted_search` con allowlist | puente opcional a `the-newsbreakers/api/trusted_search.py` | 2 días |

---

### 2.8 Narrativas / embeddings / clustering

**Estado actual — stub/MVP keywords**

- `ai-service/narratives/engine.py`: 4 buckets (vacunas, ocultamiento, artificial, brote). Crecimiento vs ciclo anterior en SQLite.
- Grafo UI: `store.network_graph` + `NetworkGraph.tsx` (vis-network). Es grafo de co-ocurrencia fuente–enfermedad–artículo, no HDBSCAN.
- `PHASES.md` marca narrativas como parcial; embeddings stub.

**Hueco**

- No hay episodios narrativos (tiempo × geografía × claim) del PDF.
- `growth_pct` 100 % si prev=0 infla alertas en el primer ciclo.
- No hay panel “Narrativas” en el nav (el grafo las mezcla).

**Cómo implementarlo**

| Paso | Archivos / libs | Esfuerzo |
|------|-----------------|----------|
| Clustering: embeddings de claims + HDBSCAN o agglomerative | `engine.py`; `hdbscan` / sklearn | 4–5 días |
| Episodio: ventana 7 días × país × cluster | nueva tabla `narrative_episodes` | 2 días |
| UI: ruta `/narrativas` con growth sparkline | `Observatory.tsx` | 1 día |

---

### 2.9 Risk engine / alertas / HITL

**Estado actual — risk MVP; HITL a medias**

- `ai-service/risk_engine.py`: pesos que suman 1. Veredictos de producto correctos.
- Señales `narrative_growth` y `visual_anomaly` casi siempre 0 (no se pasan en `analyze_article`).
- Alertas si score ≥ 55 o veredicto en {CONTRADICHO, POSIBLEMENTE ENGAÑOSO, REVISIÓN HUMANA}.
- API: `POST /alerts/{id}/review` → `reviews` + `used_for_retraining=1` **sin usar ese flag para nada**.
- Frontend: `api.review()` **existe y no se llama** desde ninguna pantalla. No hay cola “pendiente de analista”.
- Fase 18 (reentrenamiento desde feedback): no implementada.

**Hueco**

- El analista no puede aceptar/rechazar en la sala.
- `used_for_retraining` es ruido.
- No hay roles, cola, SLA, ni notificación (correo/Teams).
- Explicación de alerta es el JSON `why` del risk, no la cadena completa de `TRACEABILITY.md`.

**Cómo implementarlo**

| Paso | Archivos / libs | Esfuerzo |
|------|-----------------|----------|
| Panel HITL: lista `alerts?status=pending_review` + botones | nuevo `HitlPanel.tsx`; usar `api.review` | 1–2 días |
| Pasar `narrative_growth` y `image_reuse` reales a `risk_score` | `pipeline/run.py` `analyze_article` | 0.5 día |
| No marcar `used_for_retraining` hasta que exista dataset de feedback | `store.review_alert` | 15 min |
| Cadena TRACEABILITY en `alerts.explanation` | `run.py` al crear alerta | 1 día |

---

### 2.10 Dashboard UX (sala, mapa, gráficas, grafo, fichas)

**Estado actual — MVP UI (la parte más madura del framework)**

- Vite + React 18, puertos 5173 / API 8010.
- Rutas: `/` sala, `/mapa`, `/graficas`, `/grafo`, `/fuentes`, `/cnn`, `/article/:id`.
- Leaflet + centroides; Recharts; vis-network; fichas con claims, evidencia, geo, similares, calidad de explicación.
- Polling 60 s. Botón “Ejecutar ciclo”. Banner MySQL / última minería.
- Allowlist de URLs en cliente (`safeUrl.ts`) alineada con backend.
- **No** es el HTML del Generador. Docs viejos aún dicen lo contrario (corregido en esta auditoría).

**Hueco**

- Sin panel de alertas HITL (arriba).
- Mapa: geocodificación por país (ISO), no por estado/municipio (el gazetteer de estados existe y casi no se usa en el mapa).
- Sin auth; cualquiera en LAN con CORS localhost.
- Ficha YouTube/social depende de corpus importado del Generador (`import_corpus.py`), no de minería RSS.
- `GET /pipeline/status` documentado en monitoring y **no existe** (sí hay `/health` y `/status`).

**Cómo implementarlo**

| Paso | Archivos / libs | Esfuerzo |
|------|-----------------|----------|
| HITL en nav | `AppHeader.tsx`, panel nuevo | 1–2 días |
| Mapa: usar `STATE` entities + centroides MX | `geo.py`, `geoCentroids.ts` | 2 días |
| Token opcional `X-TNB-TOKEN` en API + header fetch | `api/main.py`, `api.ts` | 0.5 día |
| Tests e2e Playwright de sala → ficha | nuevo `frontend/e2e` | 2 días |

---

### 2.11 Automatización 24/7 (sleep, Windows service, Docker)

**Estado actual — bucle; no servicio**

- `python mine_loop.py` / `run_cycle.py --loop --interval 1800`.
- `TNB_MINE_INTERVAL_MINUTES=30`. Sleep según `next_check` o intervalo fijo.
- `mine_state.json` para el banner.
- Docker: MySQL útil; `gateway` profile **no monta Generador**, `TNB_DEMO_ROOT=/legacy` incorrecto, no incluye frontend ni `mine_loop`.
- No NSSM, no Task Scheduler XML, no Celery/Beat (Fase 20).
- `TNB_FAST=1` default hace el “24/7” demasiado agresivo con las fuentes.

**Hueco**

- Si OneDrive bloquea `tnb.db`, el loop muere. Sin watchdog.
- PC en sleep = no hay minería. Sin servicio que despierte o corra en servidor.
- Compose no orquesta API + Vite + mine.

**Cómo implementarlo**

| Paso | Archivos / libs | Esfuerzo |
|------|-----------------|----------|
| Task Scheduler: `scripts/instalar-mineria.xml` llamando `.venv\Scripts\python.exe mine_loop.py` | nuevo `scripts/` | 0.5 día |
| Opcional NSSM `tnb-mine` + `tnb-api` | scripts PowerShell | 1 día |
| Compose `app` + `mine` + `web` (nginx estático del `vite build`) | `docker-compose.yml`, Dockerfiles | 3 días |
| Watchdog: si ciclo > N min, log + skip | `mine_loop.py` | 0.5 día |
| Celery: **no** en las 4 semanas; el proceso único basta | — | P2 |

---

### 2.12 Tests, seguridad, `.env`, secretos

**Estado actual — tests MVP; seguridad demo**

- Pytest: `test_ingestion`, `test_pipeline`, `test_mining`, `test_enrich`. Cubren catálogo, dedup, NLI, risk, ciclo seed, CNN export, enrich.
- `.env` en `.gitignore`. `.env.example` con `tnb/tnb` (aceptable como ejemplo, no como prod).
- Compose: `MYSQL_ROOT_PASSWORD=tnbroot` en claro.
- API sin autenticación: `POST /cycle` dispara el pipeline; upload a `/cnn/predict`.
- CORS solo localhost:5173/5174.
- `llm.py` lee keys de `.env` hermano.
- No CI en este repo (el CI de GitHub está en `the-newsbreakers`, no aquí).
- `robots_allowed` unused; User-Agent identificable (bien).

**Hueco**

- Sin tests de integración RSS real (mocked XML sí).
- Sin SAST, rate limit, ni bind explícito 127.0.0.1 en uvicorn documentado como obligatorio.
- Dockerfile gateway `0.0.0.0:8010` sin auth.

**Cómo implementarlo**

| Paso | Archivos / libs | Esfuerzo |
|------|-----------------|----------|
| Token de API + uvicorn `--host 127.0.0.1` en README | `api/main.py`, README | 0.5 día |
| GitHub Actions pytest en el framework | `.github/workflows/ci.yml` | 0.5 día |
| No commitear `.env`; rotar si se copió | ya gitignored | verificar |
| Rate-limit `/cycle` | slowapi | 0.5 día |

---

### 2.13 Datos de calidad (seed vs minería real, FAO 404, URLs fake)

**Estado actual — mixto; hay higiene, sigue habiendo teatro**

- `TNB_DEMO_SEED` default **1** en `run_cycle.py`: si RSS no trae salud animal, inyecta 3 fixtures (WOAH, FAO, rumor sin URL).
- `mine_loop.py` pone `TNB_DEMO_SEED=0` (correcto para minería).
- `TNB_IMPORT_CORPUS=1` importa SQLite/dashboard del Generador (YouTube/social). Calidad depende de ese Excel.
- `purge_fake_urls()` borra `example.invalid`, `example.com`, `social.local`, demos.
- `safe_urls.py` allowlist + blocked hosts.
- FAO `animal-health/en` y homes genéricos siguen en seed y evidencia.
- CNN y thumbnails sintéticos se ven “como datos” en la sala.
- GDELT articles sin cuerpo se analizan igual (relevancia baja o claims pobres).

**Origen Generador (glance)**

- Pipeline batch ~40–60 min: scrape HTTP “smart” → Excel `salida/urls_enfermedades.xlsx` + HTML + DuckDB.
- `datos/source_registry.yaml` es la watchlist madre.
- `newsbreakers/` (claim_engine, dictionaries, filters) es lo que el framework importa.
- El Generador **sí** baja páginas; el framework **aún no**. La calidad histórica vive en Excel/DuckDB, no en `tnb.db`, salvo `import_corpus`.

**Hueco**

- Demo seed enmascara un día sin RSS relevantes.
- Evidencia FAO 404 enseña links muertos en fichas.
- Import corpus puede reintroducir URLs dudosas si el Excel las tiene.

**Cómo implementarlo**

| Paso | Archivos / libs | Esfuerzo |
|------|-----------------|----------|
| `TNB_DEMO_SEED=0` default; `--demo-seed` solo en README de demo | `run.py` | 15 min |
| HEAD/GET periódico de URLs de evidencia; marcar `http_status` | `enrich.py` + job | 1 día |
| Corregir FAO/EMPRES y no usar homepage como evidencia de un claim | `DISEASE_EVIDENCE` | 0.5 día |
| `import_corpus`: pasar por `is_fake_url` / allowlist (ya parcialmente) | `import_corpus.py` | 0.5 día |
| Banner UI: “N artículos de seed / corpus / rss” | KPIs + `raw_format` | 0.5 día |

---

### 2.14 Documentación y onboarding

**Estado actual — abundante y a veces contradictoria**

| Doc | Utilidad | Problema |
|-----|----------|----------|
| `README.md` | Arranque correcto (8010 + 5173) | No enlazaba esta auditoría |
| `docs/ARCHITECTURE.md` | Embudo 0–9 excelente | Decía que la UI canónica era el HTML del Generador |
| `docs/PHASES.md` | Honestidad `[x]/[~]/[ ]` | Varios `[x] DONE MVP` suenan a producción |
| `docs/MIGRATION.md` | Mapa Generador → framework | UI canónica desactualizada |
| `docs/TRACEABILITY.md` | Contrato de alerta | No se serializa así en DB |
| `monitoring/README.md` | Intención | Endpoint `/pipeline/status` inexistente |
| `tests/README.md` | pytest | OK |
| Generador `README.md` | Excel/HTML | Producto distinto; hay que decirlo en el primer párrafo del framework |

Onboarding real hoy: venv → `run_cycle.py` → uvicorn → `npm run dev`. Dependencia dura de la carpeta hermana Generador (`TNB_DEMO_ROOT`) para diccionarios. Sin Generador, keywords caen al `FALLBACK_KEYWORDS` corto.

**Cómo implementarlo**

| Paso | Esfuerzo |
|------|----------|
| README: tres productos + link `docs/AUDITORIA.md` | 15 min (hecho) |
| Copiar `diseases.yaml` mínimo **dentro** del framework para onboarding sin Generador | 0.5 día |
| Un `docs/ONBOARDING.md` de 1 página (puertos, seed off, MySQL opcional) | 0.5 día |
| Dejar de marcar Fase 4–8 como DONE sin asterisco “heurístico” | al actualizar PHASES |

---

## 3. Mapa de madurez (resumen)

| # | Área | Madurez | Bloquea 24/7 real |
|---|------|---------|-------------------|
| 1 | Ingesta | MVP | Sí (90 % scrape deferred, sin cuerpo) |
| 2 | Persistencia | MVP | Parcial (sin backup) |
| 3 | Dedup | MVP / stub semántico | No para volumen actual |
| 4 | NLP | MVP léxico | Calidad de claims |
| 5 | LLM | MVP contrato | No (correctamente opcional) |
| 6 | Visión | Académico sintético | CNN no usable en campo |
| 7 | Evidence / NLI | MVP léxico | **Sí — falsos Supported** |
| 8 | Narrativas | Stub/keywords | No para demo |
| 9 | Risk / HITL | Risk MVP, HITL UI stub | Sí para operación humana |
| 10 | Dashboard | MVP rico | No |
| 11 | 24/7 | Bucle | Sí (sleep PC, no servicio) |
| 12 | Tests / secretos | MVP / demo-inseguro | Auth |
| 13 | Datos | Seed+corpus | Sí (FAO, seed default) |
| 14 | Docs | Buenas, desalineadas | Onboarding |

---

## 4. Roadmap 4 semanas (P0 / P1 / P2)

Supuesto: un desarrollador a tiempo casi completo + alguien que etiquete fotos/alertas.

### Semana 1 — P0 calidad de señal

1. RSS reales + cuerpo de artículo (trafilatura + robots).  
2. `TNB_DEMO_SEED=0` y `TNB_FAST=0` por defecto en minería; seed solo con flag.  
3. URLs oficiales vivas (FAO/WOAH/SENASICA) + no usar homepages como evidencia.  
4. Endurecer NLI (Unknown por defecto; Supported solo con overlap fuerte o modelo).  

### Semana 2 — P0 operación

5. Panel HITL en el dashboard (cablear `POST /alerts/{id}/review`).  
6. Token API + bind 127.0.0.1; backup SQLite diario.  
7. Task Scheduler / NSSM para `mine_loop.py` + uvicorn.  
8. MySQL: tablas `reviews`/`audit_logs` + no mentir si dual-write falla.  

### Semana 3 — P1 inteligencia

9. Dataset CNN real (bloquear sintéticos) + EasyOCR.  
10. Embeddings MiniLM + near-dup semántico.  
11. Retrieval cache de fichas WOAH por enfermedad.  
12. Tests CI + métrica “% artículos con `raw_format=rss|api` vs seed”.  

### Semana 4 — P1/P2 producto

13. Narrativas por clustering (aunque sea agglomerative).  
14. Mapa por estado MX.  
15. Ampliar enfermedades del PDF (PPA, rabia, EEB) en diccionario y pills.  
16. CLIP o pHash DCT (uno de los dos). Compose API+web documentado. Celery **fuera** de las 4 semanas.

### P2 (después)

- spaCy NER, HDBSCAN, WAHIS API, Postgres/pgvector, Prometheus, roles analista, scrape SENASICA con parser versionado, reentrenamiento HITL→CNN.

---

## 5. Top 10 mejoras P0

1. **Cuerpo de artículo + más RSS** — sin texto no hay claims; hoy ~8 feeds y solo summaries.  
2. **Apagar seed/fast por defecto** — `TNB_DEMO_SEED` y `TNB_FAST` maquillan el 24/7.  
3. **Evidencia oficial viva** — reemplazar FAO 404 y homes; snippets reales cacheados.  
4. **NLI conservador** — el overlap ≥ 3 tokens produce Supported falso; Unknown debe ser el default.  
5. **UI HITL** — la API ya existe; la sala no muestra cola `pending_review`.  
6. **Auth mínima + bind local** — `POST /cycle` y uploads abiertos.  
7. **Backup de `tnb.db`** — OneDrive + WAL sin copia = pérdida del observatorio.  
8. **Servicio Windows (Task Scheduler)** — `mine_loop.py` no sobrevive sleep/reboot.  
9. **No exportar PNG sintéticos al dataset CNN** — la red “99 %” no ve fotos reales.  
10. **MySQL parity (`reviews`, `audit_logs`) o documentar SQLite-only** — dual-write hoy pierde la auditoría HITL.

---

## 6. Qué no hacer (4 semanas)

- No reescribir el verificador Next.js ni fusionar repos.  
- No scrapear “todo Internet” ni activar scrape masivo de las 100 fuentes.  
- No usar la CNN como detector de fake news.  
- No dejar que Ollama escriba el `verdict`.  
- No migrar a Celery/Postgres/Mongo hasta que un proceso + SQLite+MySQL aguante una semana de minería real.  
- No implementar “todo el PDF” (GKG, 5 indicadores compuestos, rabia/EEB) antes de que H5N1/barrenador/PPC tengan cuerpos + evidencia viva.

---

## 7. Apéndice — archivos ancla

| Pieza | Ruta |
|-------|------|
| Ciclo | `pipeline/run.py`, `mine_loop.py`, `run_cycle.py` |
| Watchlist | `ingestion/sources/catalog.yaml`, `rss_overrides.yaml` |
| Store | `database/store.py`, `mysql_mirror.py`, `mysql/schema.sql` |
| NLP | `ai-service/nlp/*.py` |
| Visión | `ai-service/vision/*.py` |
| NLI / LLM | `ai-service/verification/nli.py`, `llm.py` |
| Evidencia | `evidence-service/retrieve.py`, `database/enrich.py` |
| Risk | `ai-service/risk_engine.py` |
| API | `api/main.py` |
| UI | `frontend/src/Observatory.tsx`, `AnalysisPage.tsx` |
| Origen Excel | `Generador_Excel_Enfermedades/datos/source_registry.yaml`, `newsbreakers/` |
