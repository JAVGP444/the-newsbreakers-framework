# The NewsBreakers

<p align="center">
  <img src="branding/logo.png" width="168" alt="The NewsBreakers">
</p>

Observatorio de salud animal (gusano barrenador, gripe aviar, peste porcina). Versión **NewsBreakers 2.59.54 a.m.** Al abrir entra a la sala.

## Mac (esta versión)

Python 3.12+, Node 18+ y Git. En Terminal, en el Escritorio:

```bash
git clone https://github.com/JAVGP444/the-newsbreakers-framework.git
cd the-newsbreakers-framework
chmod +x packaging/mac/make_dmg.sh packaging/mac/install.sh mac/*.command
bash packaging/mac/make_dmg.sh
```

Sale `NewsBreakers 2.59.54 a.m..app` en el Escritorio y un `.dmg` / `.pkg`. Ábrela desde el Escritorio o Arrástrala a Aplicaciones. La primera vez tarda un minuto. Si macOS bloquea: clic derecho → Abrir.

Para trabajar desde la carpeta, sin generar el `.app`: `mac/Instalar-y-abrir.command`.

## Windows

El `.exe` se construye **en Windows**. No se cruza con el `.app`.

1. Instala [Python 3.12](https://www.python.org/downloads/) (marca **Add python.exe to PATH**), [Node.js LTS](https://nodejs.org/) y [Git](https://git-scm.com/download/win).
2. Opcional: [Inno Setup 6](https://jrsoftware.org/isinfo.php) para `NewsBreakers-Setup.exe`.
3. En **cmd**:

```bat
cd %USERPROFILE%\Desktop
git clone https://github.com/JAVGP444/the-newsbreakers-framework.git
cd the-newsbreakers-framework
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

Sale `dist\NewsBreakers\NewsBreakers.exe`. Datos en `%APPDATA%\TheNewsBreakers`.

```bat
"%LocalAppData%\Programs\Inno Setup 6\ISCC.exe" packaging\windows\setup.iss
```

## Linux

`python packaging/build.py` → `dist/NewsBreakers/` + `.desktop`.

## Tests

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m pytest tests -q
```

Briefing: [`docs/The-NewsBreakers-observatorio.pdf`](docs/The-NewsBreakers-observatorio.pdf).
