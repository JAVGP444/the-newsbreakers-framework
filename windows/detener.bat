@echo off
title The NewsBreakers — detener
echo Cerrando puertos 8010 y 5173 ...
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8010" ^| findstr LISTENING') do taskkill /F /PID %%p >nul 2>&1
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":5173" ^| findstr LISTENING') do taskkill /F /PID %%p >nul 2>&1
echo Listo.
exit /b 0
