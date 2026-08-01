@echo off
chcp 65001 >nul
setlocal EnableExtensions EnableDelayedExpansion
pushd "%~dp0"
if not exist "logs" mkdir "logs"
set "KUTANLAB_MENU=1"
:menu
cls
echo ========================================
echo KUTANLAB - TRIaje 360
echo ========================================
echo 1. Iniciar aplicación
echo 2. Probar toda la instalación
echo 3. Instalar o reparar
echo 4. Detener aplicación
echo 5. Abrir carpeta de logs
echo 6. Salir
echo ========================================
choice /C 123456 /N /M "Seleccione una opción [1-6]: "
if errorlevel 6 goto :exit
if errorlevel 5 goto :logs
if errorlevel 4 call "03_DETENER_TRIAJE360.bat"& goto :return
if errorlevel 3 call "00_INSTALAR_O_REPARAR.bat"& goto :return
if errorlevel 2 call "01_PROBAR_TODO.bat"& goto :return
if errorlevel 1 call "02_INICIAR_TRIAJE360.bat"& goto :return
:logs
start "" "%~dp0logs"
goto :return
:return
echo.
pause
goto :menu
:exit
popd
exit /b 0
