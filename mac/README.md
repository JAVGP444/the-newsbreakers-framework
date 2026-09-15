# Observatorio en Mac

Versión **NewsBreakers 2.59.54 a.m.** (Vite 5173 + API 8010).

Repo: `https://github.com/JAVGP444/the-newsbreakers-framework`

## Instalar la app

```bash
cd ~
git clone https://github.com/JAVGP444/the-newsbreakers-framework.git
cd the-newsbreakers-framework
chmod +x packaging/mac/make_dmg.sh mac/*.command
bash packaging/mac/make_dmg.sh
```

Queda `NewsBreakers 2.59.54 a.m..app` en el Escritorio. Ábrela; la primera vez tarda un minuto.

## Desde la carpeta (desarrollo)

```bash
chmod +x mac/Instalar-y-abrir.command mac/detener.command mac/minar.command mac/minar-ya.command
```

Clic derecho en `mac/Instalar-y-abrir.command` → **Abrir**. Para parar: `mac/detener.command`.

Requisitos: `python3` y `node`. Si faltan: `brew install python node`.

Opcional: carpeta hermana `Generador_Excel_Enfermedades`. Si existe, se usa como corpus local.

## Minería

`mac/minar-ya.command` corre varios ciclos seguidos. `mac/minar.command` deja el bucle en primer plano. Log: `logs/mac-mine.log`.

## MySQL (opcional)

No hace falta para abrir la UI. El ciclo usa SQLite.

```bash
docker compose up -d mysql
```

## URLs (modo carpeta)

| Servicio | URL |
|----------|-----|
| Observatorio | http://127.0.0.1:5173/#/ |
| API | http://127.0.0.1:8010 |
