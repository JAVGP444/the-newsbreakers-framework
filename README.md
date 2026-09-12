# The NewsBreakers

<p align="center">
  <img src="branding/logo.png" width="168" alt="The NewsBreakers">
</p>

Observatorio de salud animal (gusano barrenador, gripe aviar, peste porcina).

Entras con correo y contraseña. Sin TNB1 ves **cuatro notas**. Con clave se abre la sala. Cada licencia vale en **3 equipos**.

## Instalador (lo que se entrega al cliente)

El `.exe` se construye **en Windows**. El `.app` se construye **en Mac**. No se cruza.

### Windows (paso a paso, para que quede como en Mac)

En el PC Windows, no en el Mac:

1. Instala [Python 3.12](https://www.python.org/downloads/) y marca **Add python.exe to PATH**.
2. Instala [Node.js LTS](https://nodejs.org/).
3. Instala [Git](https://git-scm.com/download/win).
4. Clona este repo en el Escritorio:

```bat
cd %USERPROFILE%\Desktop
git clone https://github.com/JAVGP444/the-newsbreakers-framework.git
cd the-newsbreakers-framework
```

5. (Opcional, recomendado) Inno Setup 6: https://jrsoftware.org/isinfo.php — sale `NewsBreakers-Setup.exe`.
6. Abre **cmd** en esa carpeta y corre:

```bat
python -m venv .venv
.venv\Scripts\activate
python -m pip install -U pip
python -m pip install -r requirements.txt pyinstaller pywebview
cd frontend
npm install
set VITE_API_URL=
npm run build
cd ..
python packaging/build.py
```

7. Sale `dist\NewsBreakers\NewsBreakers.exe`. Ábrelo: ventana propia, no Chrome. Datos en `%APPDATA%\TheNewsBreakers` (como Application Support en Mac).
8. Si instalaste Inno Setup:

```bat
"%LocalAppData%\Programs\Inno Setup 6\ISCC.exe" packaging\windows\setup.iss
```

o abre `packaging\windows\setup.iss` con Inno y Compile. Sale `dist\NewsBreakers-Setup.exe`.

9. Primera pantalla: **crear cuenta** (correo + contraseña). Si tienes TNB1, pégala ahí. Tope: 3 equipos por clave.
10. Para que Mac y Windows compartan el tope de 3, el mismo archivo de asientos en OneDrive, en `.env` de ambos:

```
TNB_SEATS_PATH=C:\Users\TU_USUARIO\OneDrive\TheNewsBreakers\accounts.sqlite
```

En Mac, el path de OneDrive equivalente.

Sin ese path, cada máquina lleva su propio recuento.

### macOS

`python packaging/build.py` o el flujo nativo `packaging/mac` → `The-NewsBreakers.dmg`. Arrastra `NewsBreakers.app` a Aplicaciones.

### Linux

`python packaging/build.py` → `dist/NewsBreakers/` + `.desktop`.

## Arranque desde carpeta (desarrollo)

Python 3.12+ y Node 18+.

| SO | Abrir | Parar |
|----|--------|--------|
| macOS | `mac/Instalar-y-abrir.command` | `mac/detener.command` |
| Windows | `windows/abrir.bat` | `windows/detener.bat` |
| Linux | `./linux/abrir.sh` | `./linux/detener.sh` |

## Cuentas y licencia

```bash
python scripts/issue_license.py --who cliente@correo --days 365 --features mine,llm,ocr
python scripts/list_accounts.py
```

El cliente crea cuenta e inicia sesión. TNB1 suelta Sala, minería 24/7, CNN y gráficos. Sin clave, `POST /cycle` responde 402. El cuarto equipo responde 409 (`cupo`); en un equipo activo se puede cerrar sesión y, si hace falta, el vendedor lista asientos con `list_accounts.py`.

## Docker (opcional)

```bash
docker compose up -d mysql
```

La UI no necesita MySQL. SQLite es el almacén que abre el dashboard.

## Tests

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m pytest tests -q
```

Briefing: [`docs/The-NewsBreakers-observatorio.pdf`](docs/The-NewsBreakers-observatorio.pdf).
