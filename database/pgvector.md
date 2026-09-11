# pgvector

Tablas en `postgres/schema.sql`:

- `article_embeddings` — VECTOR(384)
- `claim_embeddings` — VECTOR(384)
- `image_embeddings` — VECTOR(512)

Uso previsto:

1. Deduplicación semántica (nivel 4 del embudo, umbral ~0.92 cosine).
2. Narrative Engine (clustering de claims).
3. Búsqueda de evidencia similar.

Fase 1: la extensión se crea en el `docker-compose` (`pgvector/pgvector:pg16`).
Los índices HNSW/IVFFlat se añaden cuando haya volumen:

```sql
CREATE INDEX article_embeddings_hnsw
  ON article_embeddings USING hnsw (embedding vector_cosine_ops);
```

El stub `ai-service/embeddings` devuelve ceros y `implemented: false`.
No instalar sentence-transformers / PyTorch todavía.
