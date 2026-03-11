#!/bin/bash
cd "$(dirname "$0")/.."

echo "============================================================"
echo "A-Stock K-Line Data Update Tool"
echo "Data Source: EastMoney API"
echo "============================================================"
echo

echo "[Step 1/2] Updating stock list..."
python src/downloaders/stock_list_downloader.py
if [ $? -ne 0 ]; then
    echo "Stock list update failed!"
    read -p "Press Enter to exit..."
    exit 1
fi
echo

echo "[Step 2/2] Downloading/Updating K-Line data..."
python src/downloaders/update_kline_data.py
if [ $? -ne 0 ]; then
    echo "K-Line data update failed!"
    read -p "Press Enter to exit..."
    exit 1
fi

echo
echo "============================================================"
echo "Update completed!"
echo "============================================================"
read -p "Press Enter to exit..."
