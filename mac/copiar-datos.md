# Igualar el observatorio / Match the observatory (~160 and keep growing)

[Español](#español) · [English](#english)

---

## Español

`data/processed/tnb.db` (~1.3 MB, sin API keys) **sí va en git**. Un `git pull` trae el corpus (~160 notas: 108 del Generador Excel, YouTube, redes y un poco de RSS).

Las miniaturas (`storage/images`, ~12 MB) también se versionan. No se sube `data/cnn_synth`.

### A) Esta noche: `git pull` (incluye ~160)

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

### B) Seguir creciendo: `mac/minar-ya.command`

El botón **Ejecutar ciclo** o un solo RSS **no** añade las mismas 26 URLs otra vez (salen como duplicado). Para ver el contador subir **en una sentada**:

```bash
./mac/minar-ya.command
```

Eso corre **8 ciclos seguidos** (`TNB_FAST=0`, `TNB_DEMO_SEED=0`, toda la watchlist, sin tope de 8 fuentes). En Terminal verás por qué no sube: `duplicados`, `irrelevantes`, `error fetch`. GDELT usa ventanas de fechas distintas en cada ciclo.

Minería continua (duerme ~30 min entre ciclos, logs en primer plano):

```bash
./mac/minar.command
```

No hace falta la carpeta `Generador_Excel_Enfermedades`. La watchlist está en `ingestion/sources/catalog.yaml` + `config/watchlist.yaml`. Keywords en `config/diseases.yaml`.

### C) Deja el Mac despierto

El **sleep / hibernación pausa el minero**. En Sistema → Batería, evita que se duerma mientras corre `minar.command` o `minar-ya.command`.

### D) Recargar la UI

Tras minar: recarga **http://127.0.0.1:5173/#/** o vuelve a abrir `Instalar-y-abrir.command`. La UI lee SQLite local, no MySQL.

### Plan B: AirDrop / USB (si git pull de la base falla)

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

### Qué sigue necesitando claves (no viene en git)

| Fuente | ¿En el snapshot de 160? | ¿Crece en el Mac sin claves? |
|--------|-------------------------|------------------------------|
| Corpus Excel / documentos | Sí (~108) | No (hace falta `Generador_Excel_Enfermedades`) |
| YouTube | Sí (~21 ya importados) | **No** — hace falta API key de YouTube en el Generador |
| Redes (Twitter, etc.) | Sí (~16 ya importados) | **No** — claves de redes en el Generador |
| RSS watchlist + GDELT | Pocas en el snapshot | **Sí** — `minar-ya.command` (GDELT no pide key) |
| LLM (OpenAI/Anthropic) | No hace falta para contar notas | Opcional, no decide la verdad |

**No** subas `.env` ni secretos. Docker / MySQL no hacen falta para ver las ~160 notas.

---

## English

`data/processed/tnb.db` (~1.3 MB, no API keys) **is in git**. A `git pull` brings the corpus (~160 notes: 108 from the Excel generator, YouTube, social, and some RSS).

Thumbnails (`storage/images`, ~12 MB) are also versioned. `data/cnn_synth` is not uploaded.

### A) Tonight: `git pull` (includes ~160)

On the **Mac**, stop the API/miner and update:

```bash
cd ~/the-newsbreakers-framework   # or the path where you cloned
chmod +x mac/*.command
./mac/detener.command
git pull
./mac/Instalar-y-abrir.command
```

Reload **http://127.0.0.1:5173/#/** — the KPI should be close to **~160**, not ~26.

If the pull says `tnb.db` conflicts (local changes):

```bash
./mac/detener.command
git checkout -- data/processed/tnb.db
git pull
./mac/Instalar-y-abrir.command
```

### B) Keep growing: `mac/minar-ya.command`

The **Run cycle** button or a single RSS pass **does not** add the same 26 URLs again (they come back as duplicates). To see the counter rise **in one sitting**:

```bash
./mac/minar-ya.command
```

That runs **8 cycles in a row** (`TNB_FAST=0`, `TNB_DEMO_SEED=0`, the full watchlist, no 8-source cap). In Terminal you will see why it does not grow: `duplicados`, `irrelevantes`, `error fetch`. GDELT uses different date windows each cycle.

Continuous mining (sleeps ~30 min between cycles, logs in the foreground):

```bash
./mac/minar.command
```

You do not need the `Generador_Excel_Enfermedades` folder. The watchlist is in `ingestion/sources/catalog.yaml` + `config/watchlist.yaml`. Keywords are in `config/diseases.yaml`.

### C) Keep the Mac awake

**Sleep / hibernation pauses the miner**. In System → Battery, stop it from sleeping while `minar.command` or `minar-ya.command` runs.

### D) Reload the UI

After mining: reload **http://127.0.0.1:5173/#/** or open `Instalar-y-abrir.command` again. The UI reads local SQLite, not MySQL.

### Plan B: AirDrop / USB (if the database git pull fails)

On **Windows**:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\paquete-mac.ps1
```

That leaves `~/Desktop/tnb-datos-mac.zip`. On the Mac, with the observatory stopped:

```bash
cd ~/the-newsbreakers-framework
mkdir -p data/processed storage/images
unzip ~/Downloads/tnb-datos-mac.zip
# or copy data/processed/tnb.db by hand
./mac/Instalar-y-abrir.command
```

### What still needs keys (not in git)

| Source | In the 160 snapshot? | Grows on the Mac without keys? |
|--------|----------------------|--------------------------------|
| Excel corpus / documents | Yes (~108) | No (`Generador_Excel_Enfermedades` is required) |
| YouTube | Yes (~21 already imported) | **No** — YouTube API key in the Generator |
| Social (Twitter, etc.) | Yes (~16 already imported) | **No** — social keys in the Generator |
| RSS watchlist + GDELT | Few in the snapshot | **Yes** — `minar-ya.command` (GDELT needs no key) |
| LLM (OpenAI/Anthropic) | Not needed to count notes | Optional; it does not decide truth |

**Do not** commit `.env` or secrets. Docker / MySQL are not required to see the ~160 notes.
