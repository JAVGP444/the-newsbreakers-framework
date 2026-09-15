# Observatorio en Mac / Observatory on Mac

[Español](#español) · [English](#english)

The live product is this framework (Vite **5173** + API **8010**).

**Do not clone** `https://github.com/JAVGP444/The-NewsBreakers` — that was the old demo (Next.js on port 3003) and it is not the observatory.

Correct private repo:

`https://github.com/JAVGP444/the-newsbreakers-framework`

---

## Español

GitHub no pone contraseña a una carpeta: el repo es **privado**. Tienes que iniciar sesión en GitHub (y estar invitado) para clonar.

### Checklist (5 pasos)

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
5. Cuando termine, se abre una ventana de app (sin pestañas). Para parar: doble clic en `mac/detener.command`.

Instalador empaquetado: `bash packaging/mac/make_dmg.sh`. Arrastra `NewsBreakers.app` a Aplicaciones.

Tras `git pull`, recarga la sala. Guía de datos: [`copiar-datos.md`](copiar-datos.md) si existe.

Si macOS dice que no se puede abrir el `.command`, usa el clic derecho → Abrir del paso 4. No hace falta Docker.

La primera vez instala `.venv`, `pip` y `npm`. Las siguientes solo arranca los servicios.

### Requisitos

- `python3` y `node` / `npm`. Si faltan:

```bash
brew install python
brew install node
```

Si no tienes Homebrew: [https://brew.sh](https://brew.sh)

### Detener

Doble clic en `detener.command` (cierra **8010**, **5173** y el minero si lo arrancaste).

### Minería

`mac/minar-ya.command` corre 8 ciclos seguidos (sin esperar 30 min) con logs en Terminal. `mac/minar.command` deja `python mine_loop.py` en **primer plano**. El sleep del Mac pausa el bucle. Log: `logs/mac-mine.log`.

### MySQL (opcional)

Docker **no** es necesario para abrir la UI. El ciclo usa SQLite.

```bash
docker compose up -d mysql
```

### Logs

- `logs/mac-api.log` — uvicorn (API)
- `logs/mac-web.log` — Vite (dashboard)
- `logs/mac-mine.log` — minero (`mac/minar.command`)

### URLs

| Servicio | URL |
|----------|-----|
| Observatorio | http://127.0.0.1:5173/#/ |
| API | http://127.0.0.1:8010 |
| Docs API | http://127.0.0.1:8010/docs |

Idioma de la app: botón **ES | EN** en la cabecera.

---

## English

GitHub does not put a password on a folder: the repo is **private**. You must sign in to GitHub (and be invited) to clone.

### Checklist (5 steps)

1. On the Mac, sign in to GitHub (account with access to the private repo).
2. Open Terminal and clone **this** repo:

```bash
cd ~
git clone https://github.com/JAVGP444/the-newsbreakers-framework.git
cd the-newsbreakers-framework
```

3. Mark the scripts as executable:

```bash
chmod +x mac/Instalar-y-abrir.command mac/detener.command mac/minar.command mac/minar-ya.command
```

4. First time (Gatekeeper): right-click `mac/Instalar-y-abrir.command` → **Open** → confirm. Or in Terminal: `./mac/Instalar-y-abrir.command`.
5. When it finishes, an app window opens (no browser tabs). To stop: double-click `mac/detener.command`.

Packaged installer: `bash packaging/mac/make_dmg.sh`. Drag `NewsBreakers.app` to Applications.

After `git pull`, reload the watch room.

If macOS says the `.command` cannot be opened, use right-click → Open from step 4. Docker is not required.

The first run installs `.venv`, `pip` and `npm`. Later runs only start the services.

### Requirements

- `python3` and `node` / `npm`. If missing:

```bash
brew install python
brew install node
```

If you do not have Homebrew: [https://brew.sh](https://brew.sh)

### Stop

Double-click `detener.command` (closes **8010**, **5173** and the miner if you started it).

### Mining

`mac/minar-ya.command` runs 8 cycles in a row (no 30 min wait) with Terminal logs. `mac/minar.command` leaves `python mine_loop.py` in the **foreground**. Mac sleep pauses the loop. Log: `logs/mac-mine.log`.

### MySQL (optional)

Docker is **not** required to open the UI. The cycle uses SQLite.

```bash
docker compose up -d mysql
```

### Logs

- `logs/mac-api.log` — uvicorn (API)
- `logs/mac-web.log` — Vite (dashboard)
- `logs/mac-mine.log` — miner (`mac/minar.command`)

### URLs

| Service | URL |
|---------|-----|
| Observatory | http://127.0.0.1:5173/#/ |
| API | http://127.0.0.1:8010 |
| API docs | http://127.0.0.1:8010/docs |

App language: **ES | EN** button in the header.
