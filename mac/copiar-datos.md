# Igualar el observatorio de Windows en el Mac

GitHub **no** incluye `data/processed/tnb.db` (está en `.gitignore`). El clone del Mac arranca con SQLite vacío. En Windows el observatorio lee esa base local (~160 artículos), no MySQL.

Un ciclo RSS/GDELT **no** reproduce esos 160: la mayoría son corpus importado desde `Generador_Excel_Enfermedades` (YouTube, redes, documentos), no noticias minadas esa misma tarde.

Tamaño típico de `tnb.db`: **~1.3 MB**. No lleva API keys. Las miniaturas viven en `storage/images` (~20 MB); si no las copias, las fichas abren igual (sin foto o con placeholder).

## Esta noche (USB / AirDrop / OneDrive)

En **Windows**, con la API y el minero parados un momento:

1. Copia este archivo al Mac (mismo sitio relativo dentro del repo):

   `the-newsbreakers-framework\data\processed\tnb.db`

2. Opcional, para fotos:

   `the-newsbreakers-framework\storage\images\`

3. En el Mac, cierra el observatorio (`mac/detener.command`) **antes** de sustituir `tnb.db`.
4. Deja `tnb.db` en:

   `~/the-newsbreakers-framework/data/processed/tnb.db`

   (o la ruta donde clonaste el repo).
5. Vuelve a abrir con `mac/Instalar-y-abrir.command`.
6. Recarga http://127.0.0.1:5173/#/ — el KPI debe acercarse a los **160** de Windows, no a ~26.

PowerShell en Windows (copia a un USB `E:\tnb-datos`):

```powershell
$src = "$env:USERPROFILE\OneDrive\Escritorio\the-newsbreakers-framework"
New-Item -ItemType Directory -Force -Path E:\tnb-datos\data\processed, E:\tnb-datos\storage\images | Out-Null
Copy-Item "$src\data\processed\tnb.db" E:\tnb-datos\data\processed\
Copy-Item "$src\storage\images\*" E:\tnb-datos\storage\images\ -Recurse -ErrorAction SilentlyContinue
```

En el Mac, desde la raíz del clone:

```bash
mkdir -p data/processed storage/images
cp /Volumes/USB/tnb-datos/data/processed/tnb.db data/processed/
cp -R /Volumes/USB/tnb-datos/storage/images/. storage/images/
```

AirDrop: envía solo `tnb.db` (1.3 MB) y colócalo en `data/processed/`.

**No** hace falta Docker ni MySQL en el Mac para ver esas notas. Si más tarde levantas MySQL vacío, el dual-write **no** sustituye un SQLite ya lleno: la UI sigue leyendo SQLite.

## Si no puedes copiar la base

1. `git pull` de este repo (límites de fetch más altos que el tope viejo de 8–12).
2. Doble clic en `mac/minar.command` (o `python mine_loop.py`).
3. Espera **varias horas**. El sleep/hibernación del Mac **pausa** la minería.
4. Un solo `python run_cycle.py` o el botón «Ejecutar ciclo» **no** llega a 150. Sin la carpeta `Generador_Excel_Enfermedades` tampoco se importan los ~108 documentos de corpus.

Opcional: copia también `Generador_Excel_Enfermedades` junto al repo (o a `~/Desktop/Generador_Excel_Enfermedades`) para que el siguiente ciclo importe YouTube/social/corpus.

## Qué no hacer

- No subas `.env` ni secretos.
- No hace falta meter `tnb.db` en git-lfs para esta talla; el USB/AirDrop es más simple y no deja una foto obsoleta en GitHub.
