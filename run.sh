#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
echo "Installing dependencies..."
pip install -r requirements.txt
echo "Starting TODC VB Dashboard..."
streamlit run main.py
