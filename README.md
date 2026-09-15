# The NewsBreakers

<p align="center">
  <img src="branding/logo.png" width="168" alt="The NewsBreakers">
</p>

Animal-health observatory (screwworm, avian flu, classical swine fever).

The app opens straight to the **watch room**. There is no account or license key.

**Language in the app:** use the **ES | EN** button in the header. The choice is saved on this computer.

[Español](#español) · [English](#english)

Install PDFs (same steps, printable):

- Spanish: [`docs/install-es.pdf`](docs/install-es.pdf)
- English: [`docs/install-en.pdf`](docs/install-en.pdf)

---

## Español

### Instalador

El `.exe` se construye **en Windows**. El `.app` se construye **en Mac**. No se cruza.

#### Windows

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

7. Sale `dist\NewsBreakers\NewsBreakers.exe`. Ábrelo: ventana propia, no Chrome. Datos en `%APPDATA%\TheNewsBreakers`.
8. Si instalaste Inno Setup:

```bat
"%LocalAppData%\Programs\Inno Setup 6\ISCC.exe" packaging\windows\setup.iss
```

o abre `packaging\windows\setup.iss` con Inno y Compile. Sale `dist\NewsBreakers-Setup.exe`.

#### macOS

```bash
bash packaging/mac/make_dmg.sh
```

Arrastra `NewsBreakers.app` a Aplicaciones. Guía corta: [`mac/README.md`](mac/README.md).

#### Linux

`python packaging/build.py` → `dist/NewsBreakers/` + `.desktop`.

### Arranque desde carpeta (desarrollo)

Python 3.12+ y Node 18+.

| SO | Abrir | Parar |
|----|--------|--------|
| macOS | `mac/Instalar-y-abrir.command` | `mac/detener.command` |
| Windows | `windows/abrir.bat` | `windows/detener.bat` |
| Linux | `./linux/abrir.sh` | `./linux/detener.sh` |

### Docker (opcional)

```bash
docker compose up -d mysql
```

La UI no necesita MySQL. SQLite es el almacén que abre el dashboard.

### Tests

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m pytest tests -q
```

Briefing: [`docs/The-NewsBreakers-observatorio.pdf`](docs/The-NewsBreakers-observatorio.pdf).

---

## English

### Installer

The `.exe` is built **on Windows**. The `.app` is built **on a Mac**. They do not cross.

#### Windows

On the Windows PC, not on the Mac:

1. Install [Python 3.12](https://www.python.org/downloads/) and tick **Add python.exe to PATH**.
2. Install [Node.js LTS](https://nodejs.org/).
3. Install [Git](https://git-scm.com/download/win).
4. Clone this repo on the Desktop:

```bat
cd %USERPROFILE%\Desktop
git clone https://github.com/JAVGP444/the-newsbreakers-framework.git
cd the-newsbreakers-framework
```

5. (Optional, recommended) Inno Setup 6: https://jrsoftware.org/isinfo.php — produces `NewsBreakers-Setup.exe`.
6. Open **cmd** in that folder and run:

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

7. Output is `dist\NewsBreakers\NewsBreakers.exe`. Open it: its own window, not Chrome. Data lives in `%APPDATA%\TheNewsBreakers`.
8. If you installed Inno Setup:

```bat
"%LocalAppData%\Programs\Inno Setup 6\ISCC.exe" packaging\windows\setup.iss
```

or open `packaging\windows\setup.iss` in Inno and Compile. Output is `dist\NewsBreakers-Setup.exe`.

#### macOS

```bash
bash packaging/mac/make_dmg.sh
```

Drag `NewsBreakers.app` to Applications. Short guide: [`mac/README.md`](mac/README.md).

#### Linux

`python packaging/build.py` → `dist/NewsBreakers/` + `.desktop`.

### Run from the folder (development)

Python 3.12+ and Node 18+.

| OS | Open | Stop |
|----|------|------|
| macOS | `mac/Instalar-y-abrir.command` | `mac/detener.command` |
| Windows | `windows/abrir.bat` | `windows/detener.bat` |
| Linux | `./linux/abrir.sh` | `./linux/detener.sh` |

### Docker (optional)

```bash
docker compose up -d mysql
```

The UI does not need MySQL. SQLite is the store the dashboard opens.

### Tests

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m pytest tests -q
```

Briefing: [`docs/The-NewsBreakers-observatorio.pdf`](docs/The-NewsBreakers-observatorio.pdf).
