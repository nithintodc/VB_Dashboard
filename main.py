#!/usr/bin/env python3
"""
TODC Virtual Brands Dashboard — application entry.

Run locally:
  streamlit run main.py

Or use ./run.sh from the project root.
"""
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent / ".env")
except Exception:
    pass

from doordash_dashboard import main


if __name__ == "__main__":
    main()
