"""
Store ID mapping: compare each data file’s store IDs to Airtable (three views).

- DoorDash files: column "Store ID" ↔ Airtable DD view field "Doordash StoreID"
- Uber Eats files: "Shop ID" and/or "External Store ID" ↔ Airtable UE view "UberEats UUID"
- Grubhub files: "grubhub_store_id" ↔ Airtable GH view "Grubhub CID"

Airtable: fetch_store_mapping_three_views() in airtable.py
"""

import io
import pandas as pd
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

_PROJECT_ROOT = Path(__file__).resolve().parent


def _normalize_id(val: Any) -> Optional[str]:
    """Convert to string, strip trailing .0 (CSV float artifact), ignore empty/NaN."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    s = str(val).strip()
    if s.endswith(".0") and s[:-2].isdigit():
        s = s[:-2]
    return s if s and s.upper() != "NAN" and s != "None" else None


def _read_file_to_df(file_or_path: Union[str, Path, Any]) -> Optional[pd.DataFrame]:
    """Read CSV or Excel from path or file-like (e.g. BytesFile)."""
    try:
        path_str = getattr(file_or_path, "name", None) or str(file_or_path)
        is_excel = path_str.lower().endswith((".xlsx", ".xls"))
        if hasattr(file_or_path, "getvalue"):
            buf = io.BytesIO(file_or_path.getvalue())
            return pd.read_excel(buf) if is_excel else pd.read_csv(buf)
        if hasattr(file_or_path, "read"):
            data = file_or_path.read()
            if hasattr(file_or_path, "seek"):
                file_or_path.seek(0)
            buf = io.BytesIO(data) if isinstance(data, bytes) else io.BytesIO(data.encode() if isinstance(data, str) else data)
            return pd.read_excel(buf) if is_excel else pd.read_csv(buf)
        return pd.read_excel(file_or_path) if is_excel else pd.read_csv(file_or_path)
    except Exception:
        return None


def get_store_ids_from_file(
    file_or_path: Union[str, Path, Any],
    platform: str,
) -> Set[str]:
    """
    Extract unique store IDs from a single file based on platform.
    """
    df = _read_file_to_df(file_or_path)
    if df is None or df.empty:
        return set()

    ids: Set[str] = set()
    platform_upper = platform.upper() if platform else ""

    if "DOORDASH" in platform_upper or platform == "DoorDash":
        if "Store ID" in df.columns:
            for v in df["Store ID"].dropna().astype(str):
                x = _normalize_id(v)
                if x:
                    ids.add(x)
        return ids

    if "GRUBHUB" in platform_upper or platform == "Grubhub":
        col = None
        for c in df.columns:
            if str(c).strip().lower() == "grubhub_store_id":
                col = c
                break
        if col is None and "grubhub_store_id" in df.columns:
            col = "grubhub_store_id"
        if col is not None:
            for v in df[col].dropna().astype(str):
                x = _normalize_id(v)
                if x:
                    ids.add(x)
        return ids

    if "UBER" in platform_upper or platform == "Uber Eats":
        for col_name in ("Shop ID", "External Store ID"):
            if col_name in df.columns:
                for v in df[col_name].dropna().astype(str):
                    x = _normalize_id(v)
                    if x:
                        ids.add(x)
        return ids

    return ids


def get_store_mapping_df() -> Tuple[Optional[pd.DataFrame], Optional[Dict[str, pd.DataFrame]], Optional[str]]:
    """
    Fetch Airtable: three views + DoorDash view as preview DataFrame.
    Returns (preview_df, view_dfs_by_platform, error_message).
    """
    try:
        import os
        from dotenv import load_dotenv
        load_dotenv(_PROJECT_ROOT / ".env")
        pat = os.environ.get("AIRTABLE_PAT", "").strip()
        if not pat:
            return None, None, "AIRTABLE_PAT is not set. Add it to .env to fetch store mappings."
        from airtable import fetch_store_mapping_three_views
        preview, view_dfs, err = fetch_store_mapping_three_views()
        if err:
            return None, None, err
        return preview, view_dfs, None
    except Exception as e:
        return None, None, f"Failed to fetch store mapping from Airtable: {e}"


def airtable_sets_from_platform_views(view_dfs: Dict[str, pd.DataFrame]) -> Dict[str, Set[str]]:
    """Build DoorDash / Uber Eats / Grubhub ID sets from each view using env field names."""
    from airtable import (
        STORE_FIELD_DOORDASH,
        STORE_FIELD_GRUBHUB,
        STORE_FIELD_UBER,
        extract_store_ids_from_column,
        resolve_store_id_column,
    )

    explicit_fields = {
        "DoorDash": STORE_FIELD_DOORDASH or None,
        "Uber Eats": STORE_FIELD_UBER or None,
        "Grubhub": STORE_FIELD_GRUBHUB or None,
    }
    result: Dict[str, Set[str]] = {
        "DoorDash": set(),
        "Grubhub": set(),
        "Uber Eats": set(),
    }
    for plat in ("DoorDash", "Uber Eats", "Grubhub"):
        df = view_dfs.get(plat) if view_dfs else None
        if df is None or df.empty:
            continue
        ex = explicit_fields.get(plat)
        col = resolve_store_id_column(df, plat, ex if ex else None)
        result[plat] = extract_store_ids_from_column(df, col)
    return result


def build_store_mapping_matrix(
    file_items: List[Dict[str, Any]],
    view_dfs: Optional[Dict[str, pd.DataFrame]] = None,
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Per uploaded/data file: unique IDs in file vs Airtable for that platform’s view.

    Matrix row keys: file_name, platform, store_ids_in_data, store_ids_in_airtable,
    matched_count, only_in_data_count, only_in_airtable_count,
    matched_sample, only_in_data_sample, only_in_airtable_sample.
    """
    if view_dfs is None:
        _preview, view_dfs, err = get_store_mapping_df()
        if err:
            return [], err
        if not view_dfs or all(df is None or df.empty for df in view_dfs.values()):
            return [], "Airtable returned no rows for the three views. Check PAT and view IDs."

    airtable_sets = airtable_sets_from_platform_views(view_dfs)
    matrix: List[Dict[str, Any]] = []

    for item in file_items:
        name = item.get("name", "?")
        platform = item.get("platform", "")
        file_obj = item.get("content") or item.get("path")
        if isinstance(file_obj, bytes):
            b = io.BytesIO(file_obj)
            b.name = name
            file_obj = b
        if file_obj is None:
            matrix.append({
                "file_name": name,
                "platform": platform,
                "store_ids_in_data": 0,
                "store_ids_in_airtable": len(airtable_sets.get(platform, set())),
                "only_in_data_count": 0,
                "only_in_airtable_count": 0,
                "matched_count": 0,
                "only_in_data_sample": [],
                "only_in_airtable_sample": [],
                "matched_sample": [],
            })
            continue

        data_ids = get_store_ids_from_file(file_obj, platform)
        at_set = airtable_sets.get(platform, set())
        matched = data_ids & at_set
        only_data = data_ids - at_set
        only_airtable = at_set - data_ids

        def _all_sorted(s: Set[str]) -> List[str]:
            return sorted(s)

        matrix.append({
            "file_name": name,
            "platform": platform,
            "store_ids_in_data": len(data_ids),
            "store_ids_in_airtable": len(at_set),
            "only_in_data_count": len(only_data),
            "only_in_airtable_count": len(only_airtable),
            "matched_count": len(matched),
            "only_in_data_sample": _all_sorted(only_data),
            "only_in_airtable_sample": _all_sorted(only_airtable),
            "matched_sample": _all_sorted(matched),
        })

    return matrix, None
