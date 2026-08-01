@echo off
chcp 65001 >nul
setlocal EnableExtensions EnableDelayedExpansion
pushd "%~dp0"
if not exist "logs" mkdir "logs"
set "LOG=%~dp0logs\stop.log"
echo ========================================
echo KUTANLAB - DETENER TRIaje 360
echo ========================================
if not exist ".venv\Scripts\python.exe" (
  echo ERROR: No existe el Python del entorno; no se intentó terminar ningún proceso.
  >"%LOG%" echo ERROR: Falta .venv\Scripts\python.exe.
  goto :error
)
".venv\Scripts\python.exe" "scripts\windows_launcher.py" stop --log "%LOG%"
if errorlevel 1 goto :error
echo Log: "%LOG%"
if not defined KUTANLAB_MENU pause
popd
exit /b 0
:error
echo No se pudo completar la detención segura. Consulte "%LOG%".
if not defined KUTANLAB_MENU pause
popd
exit /b 1
