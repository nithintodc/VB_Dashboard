#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
echo "Installing dependencies..."
python3 -m pip install -r requirements.txt
echo "Starting TODC VB Dashboard..."
exec python3 -m streamlit run main.py
