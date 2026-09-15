# Fases 0–20 — hoja de ruta

> **Español / English.** Hoja de ruta histórica. El estado actual del producto está en [`README.md`](../README.md).
>
> **English.** Historical roadmap. Current product status is in [`README.md`](../README.md).

**Fase 0** = observatorio vigente en
`C:\Users\javie\OneDrive\Escritorio\Generador_Excel_Enfermedades`.
**Fases 1–8, 12–14, 16–17** = MVP **ejecutable** en esta carpeta
(`the-newsbreakers-framework`): SQLite + JSONL + dashboard Vite, sin Docker.

Leyenda: `[x]` DONE (MVP) · `[~]` parcial / heurística · `[ ]` pendiente de producción

---

## Fase 0 — Observatorio Excel / HTML (DONE)

- [x] Launcher `★ THE NEWSBREAKERS.bat`
- [x] Excel + dashboard canónico HTML
- [x] `datos/source_registry.yaml` + `newsbreakers/`

---

## Fase 1 — Fundaciones (DONE MVP)

- [x] Catálogo watchlist + `parser_version` / frequency / last_checked / next_check / last_error
- [x] Persistencia local: `data/raw/` JSONL + `data/processed/tnb.db`
- [x] `storage/images/` object storage MVP
- [x] docker-compose.yml opcional (Postgres/Mongo/Redis)

## Fase 2 — Source manager (DONE MVP)

- [x] Semilla desde Generador `source_registry.yaml` + RSS overrides
- [x] Jerarquía API → RSS → scrape deferred

## Fase 3 — Scheduler (DONE MVP)

- [x] Un ciclo + `--loop` según `next_check`
- [x] Reintentos con backoff (30s / 2m / 3er fallo; `TNB_FAST=1` acorta para demo)

## Fase 4 — Ingesta (DONE MVP)

- [x] GDELT API (httpx) + RSS (título, link, summary, img URLs)
- [x] Cola `tnb:ingest` (Redis u `queue.Queue`)

## Fase 5 — Normalización (DONE MVP)

- [x] `UniversalContent` + `model_versions`

## Fase 6 — Dedup (DONE MVP)

- [x] URL existe → sha256(url) → sha256(texto). Semántica = pgvector más adelante.

## Fase 7 — Relevancia (DONE MVP)

- [x] Keywords diseases.yaml / enfermedades_config.yaml; skip &lt; 0.15

## Fase 8 — NER / NLP (DONE MVP)

- [x] Entidades disease / animal / country / org

## Fase 9 — CNN (parcial)

- [~] Módulo académico documentado + heurística `implemented=True` (8 clases, no FAKE/REAL)
- [ ] Pesos ResNet/entrenamiento en `models/cnn/`

## Fase 10 — OCR (parcial)

- [~] PaddleOCR si está; si no, alt text + `model_version=ocr_uninstalled`

## Fase 11 — Hash visual (parcial)

- [~] SHA-256 + average-hash 8×8 (stdlib/PIL). imagehash/pHash de producción pendiente

## Fase 12 — Claims (DONE MVP)

- [x] Estructura subject/predicate/object/location/animal/verifiable
- [x] Puente a `newsbreakers.analysis.claim_engine` vía `TNB_DEMO_ROOT`

## Fase 13 — Evidencia (DONE MVP)

- [x] Retrieval contra catálogo oficial / fichas de enfermedad (no web scrape masivo)

## Fase 14 — NLI (DONE MVP)

- [x] Supported / Contradicted / Unknown. El LLM no decide la verdad.

## Fase 15 — Narrativas (parcial)

- [~] Clustering por keywords (vacunas, ocultamiento, artificial) + crecimiento vs ciclo previo
- [ ] HDBSCAN + embeddings

## Fase 16 — Risk engine (DONE MVP)

- [x] Pesos: evidencia, confiabilidad de fuente, reuso pHash, severidad de claim
- [x] Veredictos: RESPALDADO / INSUFICIENTE / POSIBLEMENTE ENGAÑOSO / CONTRADICHO / REVISIÓN HUMANA

## Fase 17 — Alertas + HITL (DONE MVP)

- [x] `alerts` con `pending_review` + `reviews` + `audit_logs` (trazabilidad)

## Fase 18 — Reentrenamiento (pendiente)

- [ ] Feedback humano → dataset / model_version nueva

## Fase 19 — Dashboard 24/7 (MVP UI lista; no es el Next.js viejo)

- [~] Vite React+TS `:5173` + API `:8010` (KPIs, fuentes, claims, imágenes, alertas, análisis)
- [ ] Auth, roles analista, pgvector explorer

## Fase 20 — Automatización 24/7 (pendiente)

- [ ] Celery cluster + Beat + workers dedicados + monitoreo

## Qué no se hace

- Volver al verificador Next.js como producto.
- Scrapear “todo Internet”.
- Dejar que un LLM cierre FAKE/REAL.
- Usar la CNN como único detector de desinformación.
