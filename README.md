# The NewsBreakers — Framework (pipeline 24/7)

**Repositorio privado vigente:** https://github.com/JAVGP444/the-newsbreakers-framework

Clona **este** repo (no `The-NewsBreakers`, que era la demo vieja FastAPI+Next.js en el puerto 3003).

### Abrir en Mac

1. Entra en GitHub con una cuenta invitada al repo privado.
2. En Terminal:

```bash
cd ~
git clone https://github.com/JAVGP444/the-newsbreakers-framework.git
cd the-newsbreakers-framework
chmod +x mac/Instalar-y-abrir.command mac/detener.command
```

3. Doble clic en `mac/Instalar-y-abrir.command` (primera vez: clic derecho → Abrir).
4. El observatorio es **http://127.0.0.1:5173/#/** (Vite). La API está en **8010**.
5. Para parar: `mac/detener.command`.

Guía completa: [`mac/README.md`](mac/README.md). Docker no hace falta para ver la UI.

---

Sistema **ejecutable** de vigilancia multimodal en salud animal.

Watchlist → Scheduler → Ingesta (API→RSS→scrape diferido) → Normalizar →
Dedup → NLP + imágenes → Claims → Evidencia (no LLM-as-truth) → Riesgo →
Alertas/SQLite → Dashboard.

El producto vigente que se reutiliza (watchlist, diccionarios, Excel/HTML) es
`C:\Users\javie\OneDrive\Escritorio\Generador_Excel_Enfermedades`
(`TNB_DEMO_ROOT`). **No** es el verificador FastAPI+Next.js de `the-newsbreakers`.

**UI 24/7 de este framework:** http://127.0.0.1:5173 (Vite). El HTML
`salida/urls_enfermedades_dashboard.html` es el observatorio Excel, no este dashboard.

Auditoría (estado vs plan, P0/P1/P2): [`docs/AUDITORIA.md`](docs/AUDITORIA.md).

## Demo completa (Windows)

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python run_cycle.py
python -m uvicorn api.main:app --host 127.0.0.1 --port 8010
```

En otra terminal:

```
cd frontend
npm install
npm run dev
```

| Servicio | Puerto |
|----------|--------|
| API FastAPI | **8010** |
| Dashboard Vite | **5173** |

Abre http://127.0.0.1:5173

Opcional, minería continua (MySQL + SQLite):

```
docker compose up -d mysql
copy .env.example .env
pip install pymysql
python mine_loop.py
```

Equivalente: `python run_cycle.py --loop --interval 1800`

Si Docker no está, instala MySQL 8 local (`database newsbreakers`, user/password `tnb`/`tnb` como en `.env.example`). Sin MySQL el ciclo sigue en SQLite y registra `MySQL no conectado`.

Si el puerto 3306 ya está ocupado (otro `mysqld`), publica el contenedor en 3307:

```
MYSQL_PORT=3307
MYSQL_PUBLISH_PORT=3307
docker compose up -d mysql
```

POST `/cycle` sigue activo. `GET /health` incluye `mysql` y `last_mine`.

Reentrenar CNN (cuando haya fotos nuevas en `models/cnn/dataset/{clase}/`):

```
python -m ai_service.vision.train_cnn
```

No se reentrena solo en cada ciclo.

Tests:

```
pytest tests -q
```

Docker (Postgres/Mongo/Redis) es **opcional**. El MVP corre con archivos locales:

- `data/raw/` JSONL (RAW, Mongo más adelante)
- `data/processed/tnb.db` SQLite (PROCESSED, fallback)
- MySQL `newsbreakers` (warehouse; dual-write si está arriba)
- `storage/images/{sha256}.{ext}` (object storage MVP)
- `models/cnn/dataset/{clase}/` (fotos minadas para la CNN, conf ≥ 0.5)

## Qué vas a VER

1. **Terminal** (tras `python run_cycle.py`): resumen en español — fuentes revisadas, scrape diferido, artículos nuevos, imágenes, claims, alertas.
2. **Dashboard** (`:5173`): KPIs, salud de fuentes, artículos con **riesgo + veredicto** (RESPALDADO / INSUFICIENTE / POSIBLEMENTE ENGAÑOSO / CONTRADICHO / REVISIÓN HUMANA — nunca fake/real), claims Supported/Contradicted/Unknown, tarjetas de imagen (tipo visual productivo, OCR, reuso pHash en %), pestaña **Revisión** HITL.
3. **Análisis** de un artículo: título, fuente, riesgo, claims, evidencia viva, fusión visual (tipo + OCR + reuso + relevancia sanidad).
4. Botón **Ejecutar ciclo** llama `POST /cycle` (si `TNB_API_TOKEN` está definido, envía `X-API-Token`).

Por defecto **no** hay semilla demo (`TNB_DEMO_SEED=0`, `TNB_FAST=0`). Solo inyecta fixtures si pones `TNB_DEMO_SEED=1` o `--demo-seed`.

## Minero 24/7 (Windows)

El Programador de tareas sobrevive un reinicio. **El sleep/hibernación del PC sigue pausando el SO** (el task no despierta el equipo).

```
powershell -ExecutionPolicy Bypass -File scripts\instalar-minero.ps1
```

Quitar: `scripts\desinstalar-minero.ps1`

Backup SQLite en cada ciclo: `data/backups/tnb-YYYYMMDD-HHMM.db` (últimas 7). Manual: `python backup_db.py`.

La API debe escucharse solo en local:

```
python -m uvicorn api.main:app --host 127.0.0.1 --port 8010
```

## Seis funciones

| Función | Dónde |
|---------|--------|
| Monitorear | `ingestion/source_catalog.py`, `scheduler.py` |
| Recolectar | `rss_fetcher.py`, `api_fetcher.py`, `access.py` |
| Comprender | `ai-service/nlp`, `ai-service/vision` |
| Verificar | `evidence-service/retrieve.py`, `verification/nli.py` |
| Narrativas | `ai-service/narratives/engine.py` (clusters por keyword) |
| Alertar | `risk_engine.py` + tablas `alerts` / `reviews` |

## Principios

- Solo watchlist. No se scrapea “todo Internet”. Sin API ni RSS → log `scrape deferred`.
- El LLM **no** cierra la verdad. NLI conservador: Unknown por defecto; Supported solo con overlap fuerte y fuente oficial.
- Visión productiva: CLIP o ResNet18 ImageNet. CNN 8 clases = laboratorio académico (no métrica de producción si se entrenó en dibujos).
- Cada predicción lleva `model_version`. Cada veredicto deja `audit_logs` (por qué).

## Variable de entorno

```
$env:TNB_DEMO_ROOT = "C:\Users\javie\OneDrive\Escritorio\Generador_Excel_Enfermedades"
```

Por defecto ya apunta a esa carpeta hermana en el Escritorio.
