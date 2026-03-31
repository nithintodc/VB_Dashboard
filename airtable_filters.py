"""
Sidebar filters: merge Airtable store-mapping views, derive unique dimension values,
subset rows by multi-select AND logic across columns, then restrict analysis by
platform store IDs (DD / UE / GH) taken from the filtered rows.
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional, Set, Tuple

import pandas as pd

from airtable import (
    STORE_FIELD_DOORDASH,
    STORE_FIELD_GRUBHUB,
    STORE_FIELD_UBER,
    extract_store_ids_from_column,
    resolve_store_id_column,
    _ensure_unique_column_names,
)


# Exact Airtable field labels (fallback: case-insensitive match on merged columns)
FILTER_DIMENSION_LABELS: Tuple[str, ...] = (
    "Account Name",
    "Licensed Virtual Brand",
    "City",
    "State",
    "QA Auditor (from Account Name)",
    "CSA name (from Account Name)",
    "Account Advisor (from Account Name)",
)


def _normalize_id(val: Any) -> Optional[str]:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    s = str(val).strip()
    if s.endswith(".0") and len(s) > 2 and s[:-2].replace("-", "").isdigit():
        s = s[:-2]
    return s if s and s.upper() != "NAN" and s != "None" else None


def merge_store_mapping_views_for_filters(view_dfs: Optional[Dict[str, pd.DataFrame]]) -> pd.DataFrame:
    """Concatenate DD / UE / GH views and dedupe by _airtable_id (one row per record)."""
    if not view_dfs:
        return pd.DataFrame()
    parts: List[pd.DataFrame] = []
    for _plat, df in view_dfs.items():
        if df is None or df.empty:
            continue
        parts.append(df.copy())
    if not parts:
        return pd.DataFrame()
    merged = pd.concat(parts, ignore_index=True)
    if "_airtable_id" in merged.columns:
        merged = merged.drop_duplicates(subset=["_airtable_id"], keep="first")
    merged = _ensure_unique_column_names(merged)
    return merged


def _cell_to_match_strings(val: Any) -> List[str]:
    """Turn an Airtable cell into discrete strings for matching multiselect options."""
    if val is None:
        return []
    try:
        if isinstance(val, float) and pd.isna(val):
            return []
    except Exception:
        pass
    if isinstance(val, list):
        out: List[str] = []
        for item in val:
            out.extend(_cell_to_match_strings(item))
        return dedupe_preserve_order(out)
    if isinstance(val, dict):
        for key in ("name", "Name", "email", "Email", "value", "Value"):
            if key in val and val[key] is not None:
                s = str(val[key]).strip()
                return [s] if s else []
        s = str(val).strip()
        return [s] if s else []
    s = str(val).strip()
    return [s] if s else []


def dedupe_preserve_order(vals: List[str]) -> List[str]:
    seen: Set[str] = set()
    out: List[str] = []
    for v in vals:
        k = v.strip()
        if k and k not in seen:
            seen.add(k)
            out.append(k)
    return out


def resolve_filter_column(merged: pd.DataFrame, label: str) -> Optional[str]:
    if merged is None or merged.empty:
        return None
    cols = list(merged.columns)
    if label in cols:
        return label
    lower_map = {str(c).strip().lower(): c for c in cols}
    key = label.strip().lower()
    if key in lower_map:
        return lower_map[key]
    # Typo tolerance: CSA Name vs CSA name
    for c in cols:
        if str(c).strip().lower().replace("  ", " ") == key:
            return c
    return None


def multiselect_widget_key(column_name: str) -> str:
    return "flt_" + hashlib.md5(str(column_name).encode("utf-8")).hexdigest()[:16]


def unique_options_for_dimensions(merged: pd.DataFrame) -> Dict[str, List[str]]:
    """Sorted unique option strings per dimension that exists on merged."""
    out: Dict[str, List[str]] = {}
    for label in FILTER_DIMENSION_LABELS:
        col = resolve_filter_column(merged, label)
        if not col or col not in merged.columns:
            continue
        opts: List[str] = []
        for v in merged[col].tolist():
            opts.extend(_cell_to_match_strings(v))
        opts = sorted(set(opts), key=lambda x: (x.lower(), x))
        if opts:
            out[col] = opts
    return out


def apply_dimension_filters(
    merged: pd.DataFrame,
    selections: Dict[str, List[str]],
) -> pd.DataFrame:
    """
    AND across dimensions: each key is a column name; if selection non-empty,
    row must match at least one selected value for that column (OR within column).
    """
    if merged is None or merged.empty:
        return merged
    df = merged
    for col, chosen in (selections or {}).items():
        if not chosen:
            continue
        if col not in df.columns:
            continue
        want = {str(x).strip() for x in chosen if str(x).strip()}
        if not want:
            continue

        def row_ok(v: Any) -> bool:
            parts = set(_cell_to_match_strings(v))
            return bool(parts & want)

        df = df[df[col].apply(row_ok)]
    return df.reset_index(drop=True)


def allowed_platform_store_ids_from_merged(filtered_merged: pd.DataFrame) -> Dict[str, Set[str]]:
    """Extract DD / UE / GH ID sets from filtered rows (one merged table has all ID columns per record)."""
    result: Dict[str, Set[str]] = {
        "DoorDash": set(),
        "Uber Eats": set(),
        "Grubhub": set(),
    }
    if filtered_merged is None or filtered_merged.empty:
        return result
    explicit = {
        "DoorDash": STORE_FIELD_DOORDASH or None,
        "Uber Eats": STORE_FIELD_UBER or None,
        "Grubhub": STORE_FIELD_GRUBHUB or None,
    }
    for plat in ("DoorDash", "Uber Eats", "Grubhub"):
        col = resolve_store_id_column(filtered_merged, plat, explicit.get(plat))
        result[plat] = extract_store_ids_from_column(filtered_merged, col)
    return result


def filter_view_dfs_by_record_ids(
    view_dfs: Optional[Dict[str, pd.DataFrame]],
    airtable_ids: Optional[Set[str]],
) -> Dict[str, pd.DataFrame]:
    """
    airtable_ids=None: no filtering (full views).
    airtable_ids=set(): keep only rows with id in set (possibly empty dataframes).
    """
    if not view_dfs:
        return {}
    if airtable_ids is None:
        return {k: (v.copy() if v is not None else v) for k, v in view_dfs.items()}
    out: Dict[str, pd.DataFrame] = {}
    for plat, df in view_dfs.items():
        if df is None or df.empty:
            out[plat] = df
            continue
        if "_airtable_id" not in df.columns:
            out[plat] = df.copy()
            continue
        sub = df[df["_airtable_id"].astype(str).isin(airtable_ids)].copy()
        out[plat] = sub
    return out


def _find_gh_col(df: pd.DataFrame) -> Optional[str]:
    for c in df.columns:
        if str(c).strip().lower() == "grubhub_store_id":
            return c
    return None


def _filter_dd_df(df: Optional[pd.DataFrame], allowed: Set[str]) -> Optional[pd.DataFrame]:
    if df is None or df.empty:
        return df
    if not allowed:
        return df.iloc[0:0].copy()
    if "Store ID" not in df.columns:
        return df.iloc[0:0].copy()
    nid = df["Store ID"].map(_normalize_id)
    return df[nid.isin(allowed)].copy()


def _filter_ue_df(df: Optional[pd.DataFrame], allowed: Set[str]) -> Optional[pd.DataFrame]:
    if df is None or df.empty:
        return df
    has_col = any(c in df.columns for c in ("Shop ID", "External Store ID"))
    if not has_col:
        return df.iloc[0:0].copy()
    if not allowed:
        return df.iloc[0:0].copy()
    mask = pd.Series(False, index=df.index)
    for col in ("Shop ID", "External Store ID"):
        if col in df.columns:
            mask = mask | df[col].map(_normalize_id).isin(allowed)
    return df[mask].copy()


def _filter_gh_df(df: Optional[pd.DataFrame], allowed: Set[str]) -> Optional[pd.DataFrame]:
    if df is None or df.empty:
        return df
    if not allowed:
        return df.iloc[0:0].copy()
    col = _find_gh_col(df)
    if not col:
        return df.iloc[0:0].copy()
    nid = df[col].map(_normalize_id)
    return df[nid.isin(allowed)].copy()


def filter_analysis_data(
    data_loaded: Optional[Dict[str, Any]],
    allowed_by_platform: Dict[str, Set[str]],
    filtering_active: bool,
) -> Optional[Dict[str, Any]]:
    """Return shallow copy of analysis payload with DataFrames restricted to allowed store IDs."""
    if not data_loaded or not filtering_active:
        return data_loaded
    out: Dict[str, Any] = {}
    for k, v in data_loaded.items():
        if k not in ("doordash", "uber_eats", "grubhub"):
            out[k] = v
    dd = data_loaded.get("doordash")
    if dd:
        allow = allowed_by_platform.get("DoorDash") or set()
        out["doordash"] = {
            "financial_df": _filter_dd_df(dd.get("financial_df"), allow),
            "sales_aggregate_df": _filter_dd_df(dd.get("sales_aggregate_df"), allow),
            "promo_df": _filter_dd_df(dd.get("promo_df"), allow),
            "ads_df": _filter_dd_df(dd.get("ads_df"), allow),
            "operations": {
                "cancellations": _filter_dd_df(dd.get("operations", {}).get("cancellations"), allow),
                "downtime": _filter_dd_df(dd.get("operations", {}).get("downtime"), allow),
                "missing_incorrect": _filter_dd_df(dd.get("operations", {}).get("missing_incorrect"), allow),
            },
        }
    ue = data_loaded.get("uber_eats")
    if ue:
        allow = allowed_by_platform.get("Uber Eats") or set()
        out["uber_eats"] = {
            "financial_df": _filter_ue_df(ue.get("financial_df"), allow),
            "inaccurate_df": _filter_ue_df(ue.get("inaccurate_df"), allow),
            "downtime_df": _filter_ue_df(ue.get("downtime_df"), allow),
        }
    gh = data_loaded.get("grubhub")
    if gh:
        allow = allowed_by_platform.get("Grubhub") or set()
        out["grubhub"] = {
            "financial_df": _filter_gh_df(gh.get("financial_df"), allow),
            "operations_df": _filter_gh_df(gh.get("operations_df"), allow),
        }
    return out
