# MongoDB — RAW (nunca guardar solo el resultado final)

El prototipo guarda un archivo JSON (`api/news_archive.json`). Aquí el crudo
vive en Mongo para poder **reprocesar** si cambia el NLP o el parser.

| Colección | Contenido |
|-----------|-----------|
| `raw_articles` | Payload original (RSS item / GDELT JSON) + `url` + `collected_at` + `source_id` + `parser_version` |
| `raw_html` | HTML/XML original (re-parse sin volver a pedir la URL) |
| `raw_posts` | Publicaciones sociales si se añaden después (no Fase 1) |
| `images_metadata` | `sha256`, `phash`, `storage_key`, `ocr_text`, `cnn_class` (el binario **no** va aquí) |
| `scraping_logs` | `source_id`, `last_checked`, `success`/`error`, `retries`, `parser_version`, `access_method` |

Índices sugeridos:

```js
db.raw_articles.createIndex({ url: 1 }, { unique: true })
db.raw_articles.createIndex({ source_id: 1, collected_at: -1 })
db.scraping_logs.createIndex({ source_id: 1, checked_at: -1 })
db.images_metadata.createIndex({ sha256: 1 })
db.images_metadata.createIndex({ phash: 1 })
```

Las imágenes pesadas van a **object storage** (`storage/local` en Fase 1).
Postgres guarda el artículo **procesado** y las FKs.
