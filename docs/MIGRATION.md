# Migración: observatorio vigente → framework

> **Español / English.** Nota histórica de migración. El producto vigente es este repo. Instalación: [`README.md`](../README.md).
>
> **English.** Historical migration note. The current product is this repo. Install: [`README.md`](../README.md).

El producto **vigente** es
`C:\Users\javie\OneDrive\Escritorio\Generador_Excel_Enfermedades`
(Excel + dashboards HTML + `newsbreakers/`).

Esta carpeta (`the-newsbreakers-framework`) es la arquitectura 24/7.
Se migra por piezas. **No se borra el Generador.**

El verificador `the-newsbreakers` (FastAPI :8000 + Next.js :3003) **ya no**
es la fuente de verdad.

## Cómo conviven

| Proceso | Dónde | Rol |
|---------|-------|-----|
| Dashboard canónico | `Generador_Excel_Enfermedades\salida\urls_enfermedades_dashboard.html` | **UI de usuario** |
| Mapa 3 pestañas | `salida\observatorio_visual.html` | Presentación (no “lo de las imágenes”) |
| Launcher | `★ THE NEWSBREAKERS.bat` | Pipeline Excel / DuckDB / HTML |
| Gateway | `the-newsbreakers-framework\api` :8010 | Ingesta opcional Fase 1 |
| Docker | esta carpeta | Postgres / Mongo / Redis opcionales |

## Mapa de código

| Hoy (Generador) | Mañana (esta carpeta) |
|-----------------|------------------------|
| `datos/source_registry.yaml` | `ingestion/sources/catalog.yaml` |
| `newsbreakers/filters/keyword_filter.py` | `ai-service/nlp/relevance.py` |
| `newsbreakers/analysis/claim_engine.py` | `ai-service/nlp/claims.py` |
| `newsbreakers/dictionaries/diseases.yaml` | NER / relevancia |
| `excel_enfermedades/embed_link_extractor.py` | señales YouTube/Social → visión |
| `scripts/export_observatorio_pdf.py` | capturas → `vision/image_hash.py` |
| `salida/*.html` | `frontend/` (documentado, no duplicado) |
| CNN / OCR | contratos en `ai-service/vision` (sin pesos en el Generador) |

## Qué no hacer

1. No apuntar `TNB_DEMO_ROOT` a `the-newsbreakers`.
2. No abrir `observatorio_visual.html` como si fuera el producto.
3. No tratar Next.js :3003 como dashboard oficial.
4. No copiar el pipeline Excel dentro de esta carpeta (se reutiliza).
