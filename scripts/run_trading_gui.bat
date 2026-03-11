@echo off
cd /d %~dp0..
cd src
python -m ui.trading.main_window
