"""
Airtable data agent for TODC VB Dashboard.

Customize this module to pull financial and marketing data from your Airtable bases.
Set your Personal Access Token via environment variable:

  export AIRTABLE_PAT="patxxxx.your_token_here"

Or create a .env file in the project root with:

  AIRTABLE_PAT=patxxxx.your_token_here

Then customize the base IDs, table names, and field mappings below to match your Airtable setup.
"""

import os
import re
import requests
import pandas as pd
from typing import Any, Dict, List, Optional, Set, Tuple
from pathlib import Path

# Load .env from project root so AIRTABLE_PAT is available (e.g. when run via Streamlit)
try:
    from dotenv import load_dotenv
    _root = Path(__file__).resolve().parent
    load_dotenv(_root / ".env")
except Exception:
    pass

# -----------------------------------------------------------------------------
# Configuration (customize these for your Airtable bases/tables)
# -----------------------------------------------------------------------------
AIRTABLE_PAT = os.environ.get("AIRTABLE_PAT", "").strip()
AIRTABLE_API_BASE = "https://api.airtable.com/v0"
AIRTABLE_META_API_BASE = "https://api.airtable.com/v0/meta"

# Default base and table IDs – replace with your own
# Find these in Airtable: Base ID is in the API docs for your base; Table ID/name is the table name or ID.
FINANCIAL_BASE_ID = os.environ.get("AIRTABLE_FINANCIAL_BASE_ID", "appXXXXXXXXXXXXXX")
FINANCIAL_TABLE_ID = os.environ.get("AIRTABLE_FINANCIAL_TABLE", "Transactions")  # or table ID

MARKETING_PROMO_BASE_ID = os.environ.get("AIRTABLE_PROMO_BASE_ID", FINANCIAL_BASE_ID)
MARKETING_PROMO_TABLE_ID = os.environ.get("AIRTABLE_PROMO_TABLE", "Marketing Promo")

MARKETING_ADS_BASE_ID = os.environ.get("AIRTABLE_ADS_BASE_ID", FINANCIAL_BASE_ID)
MARKETING_ADS_TABLE_ID = os.environ.get("AIRTABLE_ADS_TABLE", "Marketing Ads")

# Store mapping: same table (tblub3DbzKIrfh4UA), three views — one per platform column focus
# DD: https://airtable.com/.../viwBofuDyDvgxnXaJ
# UE: https://airtable.com/.../viwGcDUjJOjYo4WSu
# GH: https://airtable.com/.../viwI7x6jwp6KKHZV8
STORE_MAPPING_BASE_ID = os.environ.get("AIRTABLE_STORE_MAPPING_BASE_ID", "appmSjXVMWR99duPQ")
STORE_MAPPING_TABLE_ID = os.environ.get("AIRTABLE_STORE_MAPPING_TABLE_ID", "tblub3DbzKIrfh4UA")
STORE_MAPPING_VIEW_DOORDASH = os.environ.get("AIRTABLE_STORE_MAPPING_VIEW_DOORDASH", "viwBofuDyDvgxnXaJ")
STORE_MAPPING_VIEW_UBER_EATS = os.environ.get("AIRTABLE_STORE_MAPPING_VIEW_UBER_EATS", "viwGcDUjJOjYo4WSu")
STORE_MAPPING_VIEW_GRUBHUB = os.environ.get("AIRTABLE_STORE_MAPPING_VIEW_GRUBHUB", "viwI7x6jwp6KKHZV8")

# Store-ID fields per view (API uses field names; fldoTvcPngOM6h8Ar = Doordash StoreID)
STORE_FIELD_DOORDASH = os.environ.get("AIRTABLE_FIELD_DOORDASH_STORE_ID", "Doordash StoreID").strip()
STORE_FIELD_UBER = os.environ.get("AIRTABLE_FIELD_UBER_EATS_UUID", "UberEats UUID").strip()
STORE_FIELD_GRUBHUB = os.environ.get("AIRTABLE_FIELD_GRUBHUB_CID", "Grubhub CID").strip()


def _headers():
    """Request headers with PAT."""
    if not AIRTABLE_PAT:
        raise ValueError(
            "AIRTABLE_PAT is not set. Set the environment variable or add it to .env"
        )
    return {
        "Authorization": f"Bearer {AIRTABLE_PAT}",
        "Content-Type": "application/json",
    }


def fetch_records(
    base_id: str,
    table_id_or_name: str,
    view: Optional[str] = None,
    max_records: Optional[int] = None,
    page_size: int = 100,
    filter_formula: Optional[str] = None,
) -> list[dict]:
    """
    Fetch records from an Airtable table with pagination.

    Args:
        base_id: Airtable base ID (e.g. appXXXXXXXXXXXXXX).
        table_id_or_name: Table name or table ID.
        view: Optional view name/ID to use for sorting/filtering.
        max_records: Stop after this many records (None = fetch all).
        page_size: Records per request (max 100).
        filter_formula: Optional Airtable formula (e.g. AND({Status}='Done')).

    Returns:
        List of record dicts: [{"id": "recXXX", "createdTime": "...", "fields": {...}}, ...].
    """
    url = f"{AIRTABLE_API_BASE}/{base_id}/{table_id_or_name}"
    params = {"pageSize": min(page_size, 100)}
    if view:
        params["view"] = view
    if filter_formula:
        params["filterByFormula"] = filter_formula

    all_records = []
    offset = None

    while True:
        if offset:
            params["offset"] = offset
        if max_records and len(all_records) >= max_records:
            break
        if max_records:
            params["pageSize"] = min(page_size, max_records - len(all_records))

        r = requests.get(url, headers=_headers(), params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        records = data.get("records", [])
        all_records.extend(records)

        if max_records and len(all_records) >= max_records:
            all_records = all_records[:max_records]
            break
        offset = data.get("offset")
        if not offset:
            break

    return all_records


def fetch_base_tables_metadata(base_id: str) -> Optional[list]:
    """
    Return Airtable base schema (tables + fields). Requires PAT scope schema.bases:read.
    """
    if not base_id:
        return None
    url = f"{AIRTABLE_META_API_BASE}/bases/{base_id}/tables"
    try:
        r = requests.get(url, headers=_headers(), timeout=60)
        r.raise_for_status()
        return r.json().get("tables", [])
    except Exception:
        return None


def _find_table_meta(tables: list, table_id_or_name: str) -> Optional[dict]:
    if not tables or not table_id_or_name:
        return None
    for t in tables:
        if t.get("id") == table_id_or_name or t.get("name") == table_id_or_name:
            return t
    return None


def _primary_field_name(table_meta: dict) -> Optional[str]:
    pid = table_meta.get("primaryFieldId")
    for f in table_meta.get("fields") or []:
        if f.get("id") == pid:
            return f.get("name")
    return None


def _link_fields_from_table_meta(table_meta: dict) -> List[Tuple[str, str]]:
    """(field_name, linked_table_id) for link columns."""
    out: List[Tuple[str, str]] = []
    for fld in table_meta.get("fields") or []:
        if fld.get("type") in ("multipleRecordLinks", "singleRecordLink"):
            lid = (fld.get("options") or {}).get("linkedTableId")
            name = fld.get("name")
            if lid and name:
                out.append((str(name), str(lid)))
    return out


_FIELD_COL_SUFFIX_RE = re.compile(r"^(.+)__([0-9]+)$")


def _dataframe_columns_for_field(df: pd.DataFrame, field_name: str) -> List[str]:
    """Match Airtable field name after _ensure_unique_column_names (e.g. Name, Name__1)."""
    if df is None or df.empty:
        return []
    cols = []
    for c in df.columns:
        s = str(c)
        if s == field_name:
            cols.append(s)
            continue
        m = _FIELD_COL_SUFFIX_RE.match(s)
        if m and m.group(1) == field_name:
            g2 = m.group(2)
            if g2.isdigit() and int(g2) >= 1:
                cols.append(s)
    return cols


def _is_probable_airtable_record_id(val: Any) -> bool:
    if not isinstance(val, str):
        return False
    s = val.strip()
    return len(s) >= 15 and s.startswith("rec") and s[3:].replace("_", "").isalnum()


def _substitute_link_cell(val: Any, id_to_label: Dict[str, str]) -> Any:
    """Replace record IDs in link cells with primary-field labels from id_to_label."""
    if val is None:
        return val
    try:
        if isinstance(val, float) and pd.isna(val):
            return val
    except Exception:
        pass
    if _is_probable_airtable_record_id(val):
        return id_to_label.get(val.strip(), val)
    if isinstance(val, list):
        new_list: List[Any] = []
        for x in val:
            new_list.append(_substitute_link_cell(x, id_to_label))
        return new_list
    if isinstance(val, dict):
        return val
    return val


def _fetch_linked_table_id_to_primary(
    base_id: str,
    linked_table_id: str,
    tables_meta: list,
) -> Dict[str, str]:
    tmeta = _find_table_meta(tables_meta, linked_table_id)
    if not tmeta:
        return {}
    pname = _primary_field_name(tmeta)
    if not pname:
        return {}
    try:
        recs = fetch_records(base_id, linked_table_id, max_records=None)
    except Exception:
        return {}
    out: Dict[str, str] = {}
    for rec in recs or []:
        rid = rec.get("id")
        if not rid:
            continue
        flds = rec.get("fields") or {}
        raw = flds.get(pname)
        if raw is None:
            label = rid
        elif isinstance(raw, list):
            parts = []
            for x in raw:
                if x is None:
                    continue
                if isinstance(x, (str, int, float)):
                    parts.append(str(x).strip())
                else:
                    parts.append(str(x).strip())
            label = ", ".join(p for p in parts if p) or rid
        else:
            label = str(raw).strip() or rid
        out[str(rid)] = label
    return out


def resolve_linked_record_fields_for_dataframes(
    dataframes: List[pd.DataFrame],
    base_id: str,
    source_table_id: str,
) -> None:
    """
    In-place: replace linked-record ID arrays (rec...) with human-readable primary-field values.

    Uses the Metadata API to find link fields; if metadata fetch fails (scope/network),
    leaves frames unchanged.
    """
    dfs = [d for d in dataframes if d is not None and not d.empty]
    if not dfs:
        return
    tables_meta = fetch_base_tables_metadata(base_id)
    if not tables_meta:
        return
    src = _find_table_meta(tables_meta, source_table_id)
    if not src:
        return
    link_fields = _link_fields_from_table_meta(src)
    if not link_fields:
        return

    linked_tables_to_load: Set[str] = set()
    for field_name, linked_tid in link_fields:
        for df in dfs:
            if _dataframe_columns_for_field(df, field_name):
                linked_tables_to_load.add(linked_tid)
                break

    id_maps: Dict[str, Dict[str, str]] = {}
    for ltid in linked_tables_to_load:
        id_maps[ltid] = _fetch_linked_table_id_to_primary(base_id, ltid, tables_meta)

    for df in dataframes:
        if df is None or df.empty:
            continue
        for field_name, linked_tid in link_fields:
            id_map = id_maps.get(linked_tid) or {}
            if not id_map:
                continue
            for col in _dataframe_columns_for_field(df, field_name):
                df[col] = df[col].apply(lambda v, m=id_map: _substitute_link_cell(v, m))


def records_to_dataframe(records: list[dict], expand_fields: bool = True) -> pd.DataFrame:
    """
    Convert Airtable records to a pandas DataFrame.

    Args:
        records: List of record dicts from fetch_records().
        expand_fields: If True, use record["fields"] as columns; if False, keep "id", "createdTime", "fields".

    Returns:
        DataFrame with one row per record.
    """
    if not records:
        return pd.DataFrame()

    if expand_fields:
        rows = []
        for rec in records:
            row = {"_airtable_id": rec.get("id"), "_createdTime": rec.get("createdTime")}
            row.update(rec.get("fields", {}))
            rows.append(row)
        return pd.DataFrame(rows)
    return pd.DataFrame(records)


def _normalize_store_id(val) -> Optional[str]:
    """Match store_mapping._normalize_id behavior without importing store_mapping (avoid cycles)."""
    if val is None:
        return None
    try:
        if isinstance(val, float) and pd.isna(val):
            return None
    except Exception:
        pass
    s = str(val).strip()
    if s.endswith(".0") and len(s) > 2 and s[:-2].replace("-", "").isdigit():
        s = s[:-2]
    if not s or s.upper() == "NAN" or s == "None":
        return None
    return s


# Preferred Airtable field names per platform (first match wins)
_PLATFORM_ID_FIELD_CANDIDATES: Dict[str, List[str]] = {
    "DoorDash": [
        "Doordash StoreID",
        "DoorDash StoreID",
        "Doordash Store Id",
        "doordash_store_id",
    ],
    "Uber Eats": [
        "UberEats UUID",
        "Uber Eats UUID",
        "UberEats UUID",
        "ubereats_uuid",
    ],
    "Grubhub": [
        "Grubhub CID",
        "Grubhub Cid",
        "grubhub_cid",
        "Grubhub CID ",
    ],
}


def resolve_store_id_column(df: pd.DataFrame, platform: str, explicit: Optional[str] = None) -> Optional[str]:
    """Pick the Airtable column that holds store IDs for this platform (explicit env name first)."""
    if df is None or df.empty:
        return None
    cols = list(df.columns)
    if explicit:
        if explicit in cols:
            return explicit
        el = explicit.strip().lower()
        for c in cols:
            if str(c).strip().lower() == el:
                return c
    candidates = list(_PLATFORM_ID_FIELD_CANDIDATES.get(platform, []))
    for c in candidates:
        if c in cols:
            return c
    lowered = {str(c).strip().lower(): c for c in cols}
    for c in candidates:
        key = c.strip().lower()
        if key in lowered:
            return lowered[key]
    # Fuzzy: substring match on column names
    for c in cols:
        cl = str(c).lower()
        if platform == "DoorDash" and "doordash" in cl and "store" in cl:
            return c
        if platform == "Uber Eats" and "uber" in cl and "uuid" in cl:
            return c
        if platform == "Grubhub" and "grubhub" in cl and ("cid" in cl or "grubhub" in cl):
            return c
    return None


def extract_store_ids_from_column(df: pd.DataFrame, col: Optional[str]) -> Set[str]:
    if df is None or df.empty or not col or col not in df.columns:
        return set()
    out: Set[str] = set()
    for v in df[col].dropna():
        if isinstance(v, list):
            for item in v:
                x = _normalize_store_id(item)
                if x:
                    out.add(x)
            continue
        if isinstance(v, dict):
            for key in ("name", "Name", "id", "Id"):
                if key in v:
                    x = _normalize_store_id(v.get(key))
                    if x:
                        out.add(x)
            continue
        x = _normalize_store_id(v)
        if x:
            out.add(x)
    return out


def _ensure_unique_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Suffix duplicate column labels so Arrow/Streamlit can serialize the frame."""
    if df is None or df.empty:
        return df
    counts: Dict[str, int] = {}
    new_cols = []
    for c in df.columns:
        key = str(c)
        n = counts.get(key, 0)
        counts[key] = n + 1
        new_cols.append(key if n == 0 else f"{key}__{n}")
    out = df.copy()
    out.columns = new_cols
    return out


def fetch_store_mapping_three_views(
    base_id: Optional[str] = None,
    table_id: Optional[str] = None,
) -> Tuple[Optional[pd.DataFrame], Optional[Dict[str, pd.DataFrame]], Optional[str]]:
    """
    Fetch the same table three times — one Airtable view per platform (DD / UE / GH).

    Returns:
        preview_df: DoorDash view only (raw columns, unique labels) for UI preview / Excel sample
        view_dfs: {"DoorDash": df, "Uber Eats": df, "Grubhub": df} — used for store ID sets
        error message or None
    """
    base_id = base_id or STORE_MAPPING_BASE_ID
    table_id = table_id or STORE_MAPPING_TABLE_ID
    view_map = {
        "DoorDash": STORE_MAPPING_VIEW_DOORDASH,
        "Uber Eats": STORE_MAPPING_VIEW_UBER_EATS,
        "Grubhub": STORE_MAPPING_VIEW_GRUBHUB,
    }

    view_dfs: Dict[str, pd.DataFrame] = {}
    try:
        for plat, vid in view_map.items():
            records = fetch_records(base_id, table_id, view=vid, max_records=10000)
            df = records_to_dataframe(records) if records else pd.DataFrame()
            view_dfs[plat] = df

        _dfs_for_links = [view_dfs[k] for k in ("DoorDash", "Uber Eats", "Grubhub") if k in view_dfs]
        resolve_linked_record_fields_for_dataframes(_dfs_for_links, base_id, table_id)

        dd = view_dfs.get("DoorDash")
        preview = dd.copy() if dd is not None and not dd.empty else pd.DataFrame()
        if not preview.empty:
            preview = _ensure_unique_column_names(preview)

        return preview, view_dfs, None
    except Exception as e:
        return None, None, str(e)


# -----------------------------------------------------------------------------
# Customize these functions to map your Airtable fields to dashboard schema
# -----------------------------------------------------------------------------

def get_financial_from_airtable(
    base_id: Optional[str] = None,
    table_id: Optional[str] = None,
) -> tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    Fetch financial/transaction data from Airtable and return a DataFrame
    in the shape expected by the dashboard (columns: _date, Subtotal, Store name, Transaction type, etc.).

    Customize: base_id, table_id, and the field mapping below to match your Airtable.
    """
    base_id = base_id or FINANCIAL_BASE_ID
    table_id = table_id or FINANCIAL_TABLE_ID
    try:
        records = fetch_records(base_id, table_id, max_records=5000)
        if not records:
            return pd.DataFrame(), None
        df = records_to_dataframe(records)

        # Optionally map common field names to dashboard schema; no required columns — raw table is returned
        column_map = {
            "Date": "_date", "Order Date": "_date", "Timestamp local date": "_date",
            "Subtotal": "Subtotal", "Total": "Subtotal", "Amount": "Subtotal",
            "Store name": "Store name", "Store": "Store name",
            "Transaction type": "Transaction type", "Type": "Transaction type",
            "Final order status": "Final order status", "Status": "Final order status",
        }
        for airtable_col, dashboard_col in column_map.items():
            if airtable_col in df.columns and dashboard_col not in df.columns:
                df[dashboard_col] = df[airtable_col]
        if "_date" in df.columns:
            df["_date"] = pd.to_datetime(df["_date"], errors="coerce").dt.normalize()
        elif "Date" in df.columns:
            df["_date"] = pd.to_datetime(df["Date"], errors="coerce").dt.normalize()
        if "Subtotal" in df.columns:
            df["Subtotal"] = pd.to_numeric(df["Subtotal"], errors="coerce").fillna(0)
        if "Store name" not in df.columns:
            df["Store name"] = df.get("Store", "Unknown") if "Store" in df.columns else "Unknown"
        if "Transaction type" not in df.columns:
            df["Transaction type"] = "Order"
        df["platform"] = "Airtable"
        return df, None
    except Exception as e:
        return None, str(e)


def get_marketing_promo_from_airtable(
    base_id: Optional[str] = None,
    table_id: Optional[str] = None,
) -> tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    Fetch marketing promo data from Airtable. Dashboard expects Date, Sales, ROAS, Orders.
    Customize base_id, table_id, and column mapping to match your base.
    """
    base_id = base_id or MARKETING_PROMO_BASE_ID
    table_id = table_id or MARKETING_PROMO_TABLE_ID
    try:
        records = fetch_records(base_id, table_id, max_records=5000)
        if not records:
            return pd.DataFrame(), None
        df = records_to_dataframe(records)
        if "Date" not in df.columns:
            for c in ["Date", "Order Date", "Created"]:
                if c in df.columns:
                    df["Date"] = df[c]
                    break
        if "Date" not in df.columns:
            return None, "Marketing table must have a Date column."
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.normalize()
        df["_date"] = df["Date"]
        return df, None
    except Exception as e:
        return None, str(e)


def get_marketing_ads_from_airtable(
    base_id: Optional[str] = None,
    table_id: Optional[str] = None,
) -> tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    Fetch marketing ads/sponsored data from Airtable. Dashboard expects Date, Sales, ROAS, Orders.
    Customize base_id, table_id, and column mapping to match your base.
    """
    base_id = base_id or MARKETING_ADS_BASE_ID
    table_id = table_id or MARKETING_ADS_TABLE_ID
    try:
        records = fetch_records(base_id, table_id, max_records=5000)
        if not records:
            return pd.DataFrame(), None
        df = records_to_dataframe(records)
        if "Date" not in df.columns:
            for c in ["Date", "Order Date", "Created"]:
                if c in df.columns:
                    df["Date"] = df[c]
                    break
        if "Date" not in df.columns:
            return None, "Ads table must have a Date column."
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.normalize()
        df["_date"] = df["Date"]
        return df, None
    except Exception as e:
        return None, str(e)


# -----------------------------------------------------------------------------
# CLI: quick test (run: python airtable.py)
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    if not AIRTABLE_PAT:
        print("Set AIRTABLE_PAT in environment or .env to test.")
        exit(1)
    print("Fetching financial records (customize base/table in this file)...")
    df, err = get_financial_from_airtable()
    if err:
        print("Error:", err)
    else:
        print(f"Rows: {len(df)}")
        print(df.head() if not df.empty else "No records.")
