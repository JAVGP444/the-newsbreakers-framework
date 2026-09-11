# Observatorio en Mac

El producto vigente es este framework (Vite **5173** + API **8010**).

**No clones** `https://github.com/JAVGP444/The-NewsBreakers` — esa era la demo vieja (Next.js en el puerto 3003) y ya no es el observatorio.

Repo privado correcto:

`https://github.com/JAVGP444/the-newsbreakers-framework`

GitHub no pone contraseña a una carpeta: el repo es **privado**. Tienes que iniciar sesión en GitHub (y estar invitado) para clonar.

## Checklist (5 pasos)

1. En el Mac, inicia sesión en GitHub (cuenta con acceso al repo privado).
2. Abre Terminal y clona **este** repo:

```bash
cd ~
git clone https://github.com/JAVGP444/the-newsbreakers-framework.git
cd the-newsbreakers-framework
```

3. Marca los scripts como ejecutables:

```bash
chmod +x mac/Instalar-y-abrir.command mac/detener.command mac/minar.command mac/minar-ya.command
```

4. Primera vez (Gatekeeper): clic derecho en `mac/Instalar-y-abrir.command` → **Abrir** → confirmar. O en Terminal: `./mac/Instalar-y-abrir.command`.
5. Cuando termine, abre **http://127.0.0.1:5173/#/** (no uses `:3003`). Para parar: doble clic en `mac/detener.command`.

Tras `git pull`, SQLite incluye ~160 notas. Recarga http://127.0.0.1:5173/#/. Para crecer esta noche: `mac/minar-ya.command` (varios ciclos, logs visibles). Guía: [`copiar-datos.md`](copiar-datos.md). El sleep del Mac pausa `minar.command`.

Si macOS dice que no se puede abrir el `.command`, usa el clic derecho → Abrir del paso 4. No hace falta Docker.

La primera vez instala `.venv`, `pip` y `npm`. Las siguientes solo arranca los servicios.

## Requisitos

- `python3` y `node` / `npm`. Si faltan:

```bash
brew install python
brew install node
```

Si no tienes Homebrew: [https://brew.sh](https://brew.sh)

Opcional: carpeta hermana `Generador_Excel_Enfermedades` (junto al repo o en `~/Desktop/Generador_Excel_Enfermedades`). Si existe, se usa como `TNB_DEMO_ROOT`. Si no, el observatorio abre igual.

## Detener

Doble clic en `detener.command` (cierra **8010**, **5173** y el minero si lo arrancaste).

## Minería

`mac/minar-ya.command` corre 8 ciclos seguidos (sin esperar 30 min) con logs en Terminal. `mac/minar.command` deja `python mine_loop.py` en **primer plano**. El sleep del Mac pausa el bucle. Log: `logs/mac-mine.log`.

## MySQL (opcional)

Docker **no** es necesario para abrir la UI. El ciclo usa SQLite.

Warehouse MySQL, desde la **raíz del repo** (no desde `mac/`):

```bash
docker compose up -d mysql
```

Si 3306 ya está ocupado:

```bash
MYSQL_PORT=3307 MYSQL_PUBLISH_PORT=3307 docker compose up -d mysql
```

## Logs

- `logs/mac-api.log` — uvicorn (API)
- `logs/mac-web.log` — Vite (dashboard)
- `logs/mac-mine.log` — minero (`mac/minar.command`)

## URLs

| Servicio | URL |
|----------|-----|
| Observatorio | http://127.0.0.1:5173/#/ |
| API | http://127.0.0.1:8010 |
| Docs API | http://127.0.0.1:8010/docs |
