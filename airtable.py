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
import requests
import pandas as pd
from typing import Optional
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

# Default base and table IDs – replace with your own
# Find these in Airtable: Base ID is in the API docs for your base; Table ID/name is the table name or ID.
FINANCIAL_BASE_ID = os.environ.get("AIRTABLE_FINANCIAL_BASE_ID", "appXXXXXXXXXXXXXX")
FINANCIAL_TABLE_ID = os.environ.get("AIRTABLE_FINANCIAL_TABLE", "Transactions")  # or table ID

MARKETING_PROMO_BASE_ID = os.environ.get("AIRTABLE_PROMO_BASE_ID", FINANCIAL_BASE_ID)
MARKETING_PROMO_TABLE_ID = os.environ.get("AIRTABLE_PROMO_TABLE", "Marketing Promo")

MARKETING_ADS_BASE_ID = os.environ.get("AIRTABLE_ADS_BASE_ID", FINANCIAL_BASE_ID)
MARKETING_ADS_TABLE_ID = os.environ.get("AIRTABLE_ADS_TABLE", "Marketing Ads")

# Store mapping table (Nithin's view): maps Doordash StoreID, Grubhub CID, UberEats UUID
# URL: https://airtable.com/appmSjXVMWR99duPQ/tblub3DbzKIrfh4UA/viwBofuDyDvgxnXaJ
STORE_MAPPING_BASE_ID = os.environ.get("AIRTABLE_STORE_MAPPING_BASE_ID", "appmSjXVMWR99duPQ")
STORE_MAPPING_TABLE_ID = os.environ.get("AIRTABLE_STORE_MAPPING_TABLE_ID", "tblub3DbzKIrfh4UA")
STORE_MAPPING_VIEW_ID = os.environ.get("AIRTABLE_STORE_MAPPING_VIEW_ID", "viwBofuDyDvgxnXaJ")


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


def get_store_mapping_from_airtable(
    base_id: Optional[str] = None,
    table_id: Optional[str] = None,
    view_id: Optional[str] = None,
) -> tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    Fetch the store mapping table from Airtable (Nithin's view).
    Expected columns: Doordash StoreID, Grubhub CID, UberEats UUID (or similar).
    Returns DataFrame with normalized column names for matching.
    """
    base_id = base_id or STORE_MAPPING_BASE_ID
    table_id = table_id or STORE_MAPPING_TABLE_ID
    view_id = view_id or STORE_MAPPING_VIEW_ID
    try:
        records = fetch_records(base_id, table_id, view=view_id, max_records=10000)
        if not records:
            return pd.DataFrame(), None
        df = records_to_dataframe(records)
        # Normalize likely Airtable field names to canonical names
        col_map = {}
        for c in df.columns:
            c_lower = c.lower().strip()
            if "doordash" in c_lower and "store" in c_lower:
                col_map[c] = "doordash_store_id"
            elif "grubhub" in c_lower and ("cid" in c_lower or "id" in c_lower):
                col_map[c] = "grubhub_cid"
            elif "uber" in c_lower and ("uuid" in c_lower or "eats" in c_lower):
                col_map[c] = "ubereats_uuid"
        df = df.rename(columns=col_map)
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
