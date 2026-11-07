@echo off
chcp 65001 >nul
title Sistema de Gestion de Peajes - Aplicacion de Escritorio v3.15.0
cd /d "%~dp0"

echo ================================================================
echo   SISTEMA DE GESTION DE PEAJES DE ESCRITORIO v3.15.0
echo   CON MOTOR DE SIMULACION DE EVENTOS DISCRETOS (DES)
echo ================================================================
echo.

python -c "import sqlalchemy, customtkinter, reportlab" 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [INFO] Verificando e instalando dependencias necesarias...
    pip install -r requirements.txt
    echo.
)

python main.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Ocurrio un error al ejecutar la aplicacion.
    pause
)
