"""
Store ID mapping matrix: compare store IDs in data files vs Airtable (Nithin's view).

Mapping:
- DoorDash: "Store ID" in DD files <-> "DoorDash StoreID" in Airtable
- Grubhub: "grubhub_store_id" in GH files <-> "Grubhub CID" in Airtable
- Uber Eats: "Shop ID" or "External Store ID" in UE files <-> "UberEats UUID" in Airtable

Primary source: Airtable API (Nithin's view).
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
    # CSV exports numeric IDs as floats (e.g. "5143504.0") — strip the .0
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
    Returns set of normalized non-empty ID strings.
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


def get_store_mapping_df() -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    Get the store mapping DataFrame from Airtable API.
    Returns (df, error_message).
    """
    try:
        import os
        from dotenv import load_dotenv
        load_dotenv(_PROJECT_ROOT / ".env")
        pat = os.environ.get("AIRTABLE_PAT", "").strip()
        if not pat:
            return None, "AIRTABLE_PAT is not set. Add it to .env to fetch store mappings."
        from airtable import get_store_mapping_from_airtable
        return get_store_mapping_from_airtable()
    except Exception as e:
        return None, f"Failed to fetch store mapping from Airtable: {e}"


def get_airtable_store_id_sets(mapping_df: pd.DataFrame) -> Dict[str, Set[str]]:
    """
    From the store mapping DataFrame (CSV or Airtable),
    build sets of store IDs per platform. Handles various column names.
    """
    result: Dict[str, Set[str]] = {
        "DoorDash": set(),
        "Grubhub": set(),
        "Uber Eats": set(),
    }
    if mapping_df is None or mapping_df.empty:
        return result

    for col in mapping_df.columns:
        c = str(col).strip().lower()
        if c == "doordash_store_id" or c == "doordash storeid" or ("doordash" in c and "store" in c):
            for v in mapping_df[col].dropna().astype(str):
                x = _normalize_id(v)
                if x:
                    result["DoorDash"].add(x)
        elif c == "grubhub_cid" or c == "grubhub cid" or ("grubhub" in c and ("cid" in c or "id" in c)):
            for v in mapping_df[col].dropna().astype(str):
                x = _normalize_id(v)
                if x:
                    result["Grubhub"].add(x)
        elif c == "ubereats_uuid" or c == "ubereats uuid" or ("uber" in c and ("uuid" in c or "eats" in c)):
            for v in mapping_df[col].dropna().astype(str):
                x = _normalize_id(v)
                if x:
                    result["Uber Eats"].add(x)

    return result


def build_store_mapping_matrix(
    file_items: List[Dict[str, Any]],
    mapping_df: Optional[pd.DataFrame] = None,
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Build the matching matrix for display.

    file_items: list of dicts with keys:
        - "name": display file name
        - "platform": "DoorDash" | "Grubhub" | "Uber Eats"
        - "path" or "content": path (str) or file-like with .getvalue() (e.g. from review_data)
    mapping_df: Optional pre-loaded store mapping DataFrame (CSV or Airtable).

    Returns (matrix_rows, error_message).
    Each matrix_row has: file_name, platform, store_ids_in_data, store_ids_in_airtable,
    only_in_data_count, only_in_airtable_count, matched_count,
    only_in_data_sample, only_in_airtable_sample, matched_sample (for display).
    """
    if mapping_df is None or mapping_df.empty:
        mapping_df, err = get_store_mapping_df()
        if err:
            return [], err
        if mapping_df is None or mapping_df.empty:
            return [], "Store mapping returned no records. Ensure AIRTABLE_PAT is set in .env."

    airtable_sets = get_airtable_store_id_sets(mapping_df)
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


def build_store_mapping_matrix_with_debug(
    file_items: List[Dict[str, Any]],
    mapping_df: Optional[pd.DataFrame] = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Optional[str]]:
    """
    Same as build_store_mapping_matrix but also returns a list of debug steps
    for UI display. Returns (matrix_rows, debug_steps, error_message).
    Each debug step: {"step": str, "status": "ok"|"fail"|"info", "detail": str, "extra": optional}
    """
    debug: List[Dict[str, Any]] = []

    # Step 1: Load store mapping from Airtable API
    if mapping_df is None or mapping_df.empty:
        try:
            import os
            from dotenv import load_dotenv
            load_dotenv(_PROJECT_ROOT / ".env")
            pat = os.environ.get("AIRTABLE_PAT", "").strip()
            if not pat:
                debug.append({"step": "Airtable PAT", "status": "fail", "detail": "AIRTABLE_PAT not set in .env."})
                return [], debug, "AIRTABLE_PAT is not set. Add it to .env to fetch store mappings."
            debug.append({"step": "Airtable PAT", "status": "ok", "detail": f"Set ({len(pat)} chars)"})
            from airtable import get_store_mapping_from_airtable
            mapping_df, err = get_store_mapping_from_airtable()
            if err:
                debug.append({"step": "Fetch Airtable", "status": "fail", "detail": err})
                return [], debug, err
            if mapping_df is None or mapping_df.empty:
                debug.append({"step": "Fetch Airtable", "status": "fail", "detail": "No records returned."})
                return [], debug, "Airtable returned no records."
            debug.append({"step": "Fetch Airtable", "status": "ok", "detail": f"Fetched {len(mapping_df)} records from Airtable."})
        except Exception as e:
            debug.append({"step": "Airtable fetch", "status": "fail", "detail": str(e)})
            return [], debug, str(e)
    else:
        debug.append({"step": "Store mapping", "status": "ok", "detail": f"Using provided table ({len(mapping_df)} records)."})

    # Step 2: Show columns
    cols = list(mapping_df.columns)
    debug.append({"step": "Mapping table columns", "status": "info", "detail": ", ".join(cols) if cols else "(none)", "extra": cols})

    # Step 3: Store ID sets
    airtable_sets = get_airtable_store_id_sets(mapping_df)
    debug.append({
        "step": "Store IDs extracted from mapping",
        "status": "ok",
        "detail": f"DoorDash: {len(airtable_sets['DoorDash'])} | Grubhub: {len(airtable_sets['Grubhub'])} | Uber Eats: {len(airtable_sets['Uber Eats'])}",
        "extra": {k: len(v) for k, v in airtable_sets.items()},
    })

    # Step 5: Files to compare
    debug.append({
        "step": "Files to compare",
        "status": "info",
        "detail": f"{len(file_items)} file(s)",
        "extra": [f"{item.get('name', '?')} ({item.get('platform', '')})" for item in file_items],
    })

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
            debug.append({"step": f"Read: {name[:50]}", "status": "fail", "detail": "No path or content."})
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
        debug.append({
            "step": f"Match: {name[:50]}",
            "status": "ok",
            "detail": f"Data: {len(data_ids)} IDs | Airtable: {len(at_set)} | Matched: {len(matched)}",
            "extra": {"in_data": len(data_ids), "in_airtable": len(at_set), "matched": len(matched)},
        })

    return matrix, debug, None
