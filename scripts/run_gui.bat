@echo off
chcp 65001 >nul
title 股票行情系统
cd /d "%~dp0"
python stock_gui.py
pause
