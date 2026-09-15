# Trazabilidad / Traceability

> **Español.** Cada alerta debe poder responder: **¿por qué The NewsBreakers llegó a esta conclusión?** Si no se puede reconstruir, no se publica.
>
> **English.** Every alert must answer: **why did The NewsBreakers reach this conclusion?** If it cannot be reconstructed, it is not published.

Cada alerta debe poder responder: **¿por qué The NewsBreakers llegó a esta
conclusión?** Si no se puede reconstruir, no se publica.

## Cadena mínima

```
ALERTA #TN-00182
  Claim (texto + claim_id)
    → Evidencia A (URL, tier, stance NLI)
    → Evidencia B
    → Documento oficial C (WHO / WOAH / WAHIS / …)
    → Contradicción o respaldo (Supported | Contradicted | Unknown)
    → Imagen reutilizada (pHash / sha256) si aplica
    → Narrativa en crecimiento (narrative_id, growth_pct)
    → Risk score (pesos + partes)
    → model_name + model_version de cada etapa
    → Revisión humana (pending | accepted | rejected + motivo)
```

## Dónde se guarda

| Pieza | Tabla / colección |
|-------|-------------------|
| Explicación estructurada | `alerts.explanation` JSONB |
| Quién/qué cambió | `audit_logs` |
| Versión de modelos | `model_versions` + columnas `model_name/version` en claims, imágenes, embeddings |
| Decisión del analista | `reviews` (`used_for_retraining`) |
| Crudo irreproducible | Mongo `raw_articles` / `raw_html` |

## `explanation` (ejemplo de contrato)

```json
{
  "claim_id": "CL-001",
  "nli": {"label": "Contradicted", "model_version": "contract_v1"},
  "evidence_ids": ["EV-01", "EV-02"],
  "risk": {"score": 78, "verdict": "CONTRADICHO", "model_version": "weighted_v1"},
  "image": {"phash": null, "reuse": false},
  "narrative_id": null,
  "pipeline_level": 9
}
```

Sin estos campos, el risk engine debe forzar **REVISIÓN HUMANA**.
