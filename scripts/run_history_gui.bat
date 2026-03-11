@echo off
cd /d %~dp0..
cd src
python -m ui.history.main_window
