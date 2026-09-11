# Igualar el observatorio de Windows en el Mac (~160 y seguir creciendo)

`data/processed/tnb.db` (~1.3 MB, sin API keys) **sí va en git**. Un `git pull` trae el corpus de Windows (~160 notas: 108 del Generador Excel, YouTube, redes y un poco de RSS).

Las miniaturas (`storage/images`, ~12 MB) también se versionan. No se sube `data/cnn_synth`.

## A) Esta noche: `git pull` (incluye ~160)

En el **Mac**, para la API/minero y actualiza:

```bash
cd ~/the-newsbreakers-framework   # o la ruta donde clonaste
chmod +x mac/*.command
./mac/detener.command
git pull
./mac/Instalar-y-abrir.command
```

Recarga **http://127.0.0.1:5173/#/** — el KPI debe acercarse a **~160**, no a ~26.

Si el pull dice que `tnb.db` conflictúa (cambios locales):

```bash
./mac/detener.command
git checkout -- data/processed/tnb.db
git pull
./mac/Instalar-y-abrir.command
```

## B) Seguir creciendo: `mac/minar-ya.command`

El botón «Ejecutar ciclo» o un solo RSS **no** añade las mismas 26 URLs otra vez (salen como duplicado). Para ver el contador subir **en una sentada**:

```bash
./mac/minar-ya.command
```

Eso corre **8 ciclos seguidos** (`TNB_FAST=0`, `TNB_DEMO_SEED=0`, toda la watchlist, sin tope de 8 fuentes). En Terminal verás por qué no sube: `duplicados`, `irrelevantes`, `error fetch`. GDELT usa ventanas de fechas distintas en cada ciclo.

Minería continua (duerme ~30 min entre ciclos, logs en primer plano):

```bash
./mac/minar.command
```

No hace falta la carpeta `Generador_Excel_Enfermedades`. La watchlist está en `ingestion/sources/catalog.yaml` + `config/watchlist.yaml`. Keywords en `config/diseases.yaml`.

## C) Deja el Mac despierto

El **sleep / hibernación pausa el minero**. En Sistema → Batería, evita que se duerma mientras corre `minar.command` o `minar-ya.command`.

## D) Recargar la UI

Tras minar: recarga **http://127.0.0.1:5173/#/** o vuelve a abrir `Instalar-y-abrir.command`. La UI lee SQLite local, no MySQL.

## Plan B: AirDrop / USB (si git pull de la base falla)

En **Windows**:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\paquete-mac.ps1
```

Eso deja `~/Desktop/tnb-datos-mac.zip`. En el Mac, con el observatorio parado:

```bash
cd ~/the-newsbreakers-framework
mkdir -p data/processed storage/images
unzip ~/Downloads/tnb-datos-mac.zip
# o copia a mano data/processed/tnb.db
./mac/Instalar-y-abrir.command
```

## Qué sigue necesitando claves (no viene en git)

| Fuente | ¿En el snapshot de 160? | ¿Crece en el Mac sin claves? |
|--------|-------------------------|------------------------------|
| Corpus Excel / documentos | Sí (~108) | No (hace falta `Generador_Excel_Enfermedades`) |
| YouTube | Sí (~21 ya importados) | **No** — hace falta API key de YouTube en el Generador |
| Redes (Twitter, etc.) | Sí (~16 ya importados) | **No** — claves de redes en el Generador |
| RSS watchlist + GDELT | Pocas en el snapshot | **Sí** — `minar-ya.command` (GDELT no pide key) |
| LLM (OpenAI/Anthropic) | No hace falta para contar notas | Opcional, no decide la verdad |

**No** subas `.env` ni secretos. Docker / MySQL no hacen falta para ver las ~160 notas.
