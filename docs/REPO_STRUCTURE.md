# Repository structure

```
TODC-VB-DASHBOARD/
├── main.py                 # Streamlit entry: loads .env, calls dashboard main()
├── doordash_dashboard.py   # UI: page config, CSS, Plotly renderers, app orchestration (main())
├── data_loader.py          # CSV/XLSX discovery, platform detection, normalized analysis payloads
├── store_mapping.py        # Store ID matrix vs Airtable (three views)
├── airtable.py             # Airtable REST client + store-mapping fetches
├── todc_vb/                # Shared package
│   ├── __init__.py
│   └── config.py           # Plotly theme + color palette
├── data/                   # Sample / default CSV & Excel exports (gitignored if large)
├── docs/                   # Data and architecture notes
├── .streamlit/config.toml  # Streamlit UI defaults
├── requirements.txt
├── run.sh                  # pip install + streamlit run main.py
└── .env.example            # AIRTABLE_PAT and optional view/field overrides
```

## Execution flow

1. **`streamlit run main.py`** (or `./run.sh`) loads `main.py`.
2. **`main.py`** loads environment variables and imports **`main()`** from `doordash_dashboard`.
3. **`doordash_dashboard.main()`** orchestrates:
   - `_render_header_banner()` → `_render_sidebar_upload()` → `_handle_run_analysis_click()` (loads data + `store_mapping.build_store_mapping_matrix()` from three Airtable views)
   - Tabs: `_render_tab_data_verification()` → `_render_tab_mapping()` → `_render_tab_analysis()` (calls `render_dd_*`, `render_ue_*`, `render_gh_*`).

Platform analysis charts live in the same module as the renderers; data preparation is centralized in `data_loader.py`.
