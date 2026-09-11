# Object storage MVP — archivos en disco; metadatos en SQLite `images`.

```
storage/images/{sha256}.{ext}
```

Producción: mismo contrato hacia S3/MinIO. RAW JSONL en `data/raw/`.
PROCESSED en `data/processed/tnb.db` (Postgres más adelante).
