#!/bin/bash
cd "$(dirname "$0")/.."
cd src
python -m ui.history.main_window
