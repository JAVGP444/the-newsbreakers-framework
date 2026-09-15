# Installation (English)

Same guide as PDF: [`install-en.pdf`](install-en.pdf). Español: [`install-es.md`](install-es.md).

Animal-health observatory. The app opens to the watch room. No account or license key. Header button: **ES | EN**.

## Windows (on the Windows PC)

Python 3.12 (PATH), Node.js LTS, Git. Optional: Inno Setup 6.

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

Output: `dist\NewsBreakers\NewsBreakers.exe`. Data: `%APPDATA%\TheNewsBreakers`.

## macOS

```bash
bash packaging/mac/make_dmg.sh
```

Drag `NewsBreakers.app` to Applications. Development: `mac/Instalar-y-abrir.command`.

## Linux

`./linux/abrir.sh` or `python packaging/build.py`.
