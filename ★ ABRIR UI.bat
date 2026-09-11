@echo off
chcp 65001 >nul
title THE NEWSBREAKERS — abrir UI canónica

set "UI=C:\Users\javie\OneDrive\Escritorio\Generador_Excel_Enfermedades\salida\urls_enfermedades_dashboard.html"
set "MAP=C:\Users\javie\OneDrive\Escritorio\Generador_Excel_Enfermedades\salida\observatorio_visual.html"

echo.
echo  UI canónica (imágenes / observatorio completo):
echo    %UI%
echo.
echo  NO abras el mapa de 3 pestañas salvo que quieras presentación:
echo    %MAP%
echo.

if exist "%UI%" (
  start "" "%UI%"
  echo  Abierto.
) else (
  echo  ERROR: no existe el dashboard canónico.
  echo  Genera con:  ★ THE NEWSBREAKERS.bat solo-dashboard
  echo  en Generador_Excel_Enfermedades
  pause
  exit /b 1
)
exit /b 0
