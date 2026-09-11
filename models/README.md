# Modelos versionados

Toda predicción persiste `model_name`, `model_version`, `prediction`,
`confidence` y `timestamp` (tablas `model_versions`, columnas en claims/imágenes).

| Carpeta | Uso |
|---------|-----|
| `cnn/` | Experimento académico: clases visuales (`OFFICIAL_DOCUMENT`, `MEME`, …). **No** fake/real. |
| `nli/` | Modelo entailment (Fase 14) |
| `embeddings/` | Checkpoints texto/visión |

Human-in-the-loop: `reviews.used_for_retraining` alimenta el siguiente
entrenamiento. Generador_Excel_Enfermedades no incluye pesos CNN; el
`training/golden_dataset.jsonl` es NLP/dashboard, no fotos.
