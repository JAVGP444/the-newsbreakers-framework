# Instalación (español)

Misma guía en PDF: [`install-es.pdf`](install-es.pdf). English: [`install-en.md`](install-en.md).

Observatorio de salud animal. Al abrir entra a la sala. No hay cuenta ni clave. En la cabecera: botón **ES | EN**.

## Windows (en el PC Windows)

Python 3.12 (PATH), Node.js LTS, Git. Opcional: Inno Setup 6.

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

Sale `dist\NewsBreakers\NewsBreakers.exe`. Datos: `%APPDATA%\TheNewsBreakers`.

## macOS

```bash
bash packaging/mac/make_dmg.sh
```

Arrastra `NewsBreakers.app` a Aplicaciones. Desarrollo: `mac/Instalar-y-abrir.command`.

## Linux

`./linux/abrir.sh` o `python packaging/build.py`.
