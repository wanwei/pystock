@echo off
chcp 65001 >nul
title Stock System
cd /d "%~dp0"
cd ..
python src\stock_gui.py
pause
