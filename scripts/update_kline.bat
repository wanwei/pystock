@echo off
chcp 65001 >nul
title A-Stock K-Line Update
cd /d "%~dp0\.."

echo ============================================================
echo A-Stock K-Line Data Update Tool
echo Data Source: EastMoney API
echo ============================================================
echo.

echo [Step 1/2] Updating stock list...
python src/downloaders/stock_list_downloader.py
if errorlevel 1 (
    echo Stock list update failed!
    pause
    exit /b 1
)
echo.

echo [Step 2/2] Downloading/Updating K-Line data...
python src/update_kline_data.py
if errorlevel 1 (
    echo K-Line data update failed!
    pause
    exit /b 1
)

echo.
echo ============================================================
echo Update completed!
echo ============================================================
pause
