#!/bin/bash
cd "$(dirname "$0")/.."
cd src
python -m ui.trading.main_window
