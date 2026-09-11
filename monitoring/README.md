# Monitoreo interno

Aún no hay Prometheus/Grafana. En Fase 1 el “health” es:

- `GET http://127.0.0.1:8010/health` (SQLite, MySQL, última minería, CNN dataset)
- `GET http://127.0.0.1:8010/status` (LLM probe + pesos CNN; no existe `/pipeline/status`)
- `GET http://127.0.0.1:8010/sources` (`last_error`, `next_check`)
- RAW local: `data/raw/*.jsonl` (Mongo `scraping_logs` aún no hay cliente)

Más adelante: latencia de colas Redis, workers caídos, fuentes que fallan
N veces, espacio en object storage.
