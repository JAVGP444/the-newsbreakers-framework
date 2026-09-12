@echo off
chcp 65001 >nul
title The NewsBreakers — observatorio
cd /d "%~dp0.."

set API_PORT=8010
set WEB_PORT=5173

where python >nul 2>&1
if errorlevel 1 (
  echo Falta python. Instala Python 3.12+ y marca "Add to PATH".
  pause
  exit /b 1
)
where npm >nul 2>&1
if errorlevel 1 (
  echo Falta Node.js / npm. Instala LTS desde https://nodejs.org
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo Creando .venv ...
  python -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install -q -r requirements.txt
pushd frontend
call npm install
popd

if not exist ".env" if exist ".env.example" copy /y ".env.example" ".env" >nul

echo.
echo Repo: %CD%
echo API  http://127.0.0.1:%API_PORT%
echo UI   http://127.0.0.1:%WEB_PORT%/#/
echo.

start "tnb-api" /min cmd /c "cd /d "%CD%" && .venv\Scripts\python -m uvicorn api.main:app --host 127.0.0.1 --port %API_PORT%"
start "tnb-web" /min cmd /c "cd /d "%CD%\frontend" && npm run dev"

timeout /t 5 /nobreak >nul
if exist ".venv\Scripts\pythonw.exe" (
  start "tnb-app" .venv\Scripts\pythonw.exe desktop\open.py
) else (
  start "tnb-app" .venv\Scripts\python.exe desktop\open.py
)
echo Listo. Se abre como ventana, no como pestaña. Para parar: windows\detener.bat
exit /b 0
