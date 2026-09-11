# Arquitectura — The NewsBreakers (framework en Escritorio)

Sistema inteligente **multimodal** de vigilancia, verificación y análisis de
desinformación en **salud animal**. El producto vigente es
`C:\Users\javie\OneDrive\Escritorio\Generador_Excel_Enfermedades`
(Excel + dashboards HTML + `newsbreakers/`). Esta carpeta
(`C:\Users\javie\OneDrive\Escritorio\the-newsbreakers-framework`) es la
evolución hacia operación **24/7**.

**UI 24/7 (este repo):** dashboard Vite en http://127.0.0.1:5173 (FastAPI :8010).
No es Next.js :3003. No es `observatorio_visual.html`.

**UI del observatorio Excel (origen, carpeta hermana):**
`Generador_Excel_Enfermedades\salida\urls_enfermedades_dashboard.html`.

Estado vs plan maestro: [`AUDITORIA.md`](AUDITORIA.md).

**Stack:** gateway FastAPI (:8010) + dashboard Vite (:5173). Persistencia local
SQLite/JSONL (Postgres/Mongo/Redis opcionales). RSS/API primero; scraping al final.

---

## Seis funciones

| # | Función | Qué hace | Dónde (Fase 1) |
|---|---------|----------|----------------|
| 1 | **Monitorear** | Watchlist + scheduler por prioridad | `ingestion/source_catalog.py`, `scheduler.py` |
| 2 | **Recolectar** | API → RSS → scrape | `rss_fetcher.py`, `api_fetcher.py`, `access.py` |
| 3 | **Comprender** | NLP + visión (OCR / CNN / embeddings) | `ai-service/nlp`, `vision`, `embeddings` |
| 4 | **Verificar** | Claims + evidencia; el LLM **no** decide la verdad | `verification/nli.py`, `evidence-service` |
| 5 | **Detectar narrativas** | Clustering + crecimiento anómalo | `ai-service/narratives` (stub) |
| 6 | **Alertar** | Risk score + revisión humana + reentrenamiento | `risk_engine.py`, tablas `alerts` / `reviews` |

---

## Pipeline

```
                         INTERNET (solo watchlist)
                                |
                    RSS / APIs oficiales / HTML
                                |
                      SOURCE WATCHER (scheduler)
                       freq. por prioridad
                                |
                           INGESTION
                                |
                         NORMALIZATION
                         UniversalContent
                                |
                    DEDUP (URL → SHA-256 → texto → semántica)
                                |
                 +--------------+--------------+
                 |                             |
               TEXTO                        IMAGEN
                 |                             |
                NLP              download→validate→hash
          relevancia/NER              →pHash→OCR→CNN
             claims                    →embedding
                 |                             |
                 +--------------+--------------+
                                |
                            MULTIMODAL
                                |
                      ENTITIES  →  CLAIMS
                                |
                           EMBEDDINGS
                                |
                        NARRATIVE ENGINE
                                |
                         EVIDENCE ENGINE
                     (oficial > científica)
                                |
                      CLAIM VERIFICATION (NLI)
                   Supported / Contradicted / Unknown
                                |
                           RISK ENGINE
                                |
              ALERT  |  HUMAN REVIEW  |  DATABASE
                                |
                      FEEDBACK → MODEL IMPROVEMENT
                                |
                            DASHBOARD
```

---

## Embudo de procesamiento (niveles 0–9)

No todos los modelos para todo. Un ítem solo sube de nivel si pasa el filtro.

```
  ~100k URLs/día (watchlist, no “todo Internet”)
       │
  0  URL / RSS / API
       │  dedup
  1  recolectado
       │  keywords (config/keywords.yaml)
  2  relevancia lexical
       │  clasificador ML (pendiente)
  3  relevancia ML
       │
  4  NLP (entidades)
       │
  5  OCR / CNN / pHash (si hay imagen)
       │
  6  claims
       │
  7  evidencia + NLI
       │
  8  narrativas
       │
  9  revisión humana → alerta
       │
      decenas de alertas auditables
```

Campo `articles.pipeline_level` en Postgres.

---

## RAW + PROCESSED

| Capa | Tecnología | Contenido |
|------|------------|-----------|
| RAW | MongoDB | HTML, JSON GDELT, RSS item original |
| PROCESSED | PostgreSQL | artículos, claims, evidencia, alertas |
| VECTORES | pgvector | embeddings texto/imagen |
| BINARIOS | object storage | imágenes (`storage/local` en Fase 1) |

Reprocesar NLP v2 **sin** volver a scrapear: se lee `raw_html`.

---

## Veredictos (no FAKE/REAL como única salida)

- **RESPALDADO**
- **INSUFICIENTE**
- **POSIBLEMENTE ENGAÑOSO**
- **CONTRADICHO**
- **REVISIÓN HUMANA**

NLI interno: `Supported` | `Contradicted` | `Unknown`. El LLM puede extraer o
resumir; **no** cierra el veredicto.

---

## Principios que no se negocian

1. Watchlist de fuentes — no crawler abierto.
2. Catálogo con `parser_version` y jerarquía `api → rss → scrape`.
3. Scheduler con frecuencias por prioridad (15 / 30 / 60 / 360 / 720 min).
4. Dedup en cascada; semántica vía pgvector más adelante.
5. Evidence-first; human-in-the-loop; `model_version` en cada predicción.
6. Trazabilidad en cada alerta (`docs/TRACEABILITY.md`).
