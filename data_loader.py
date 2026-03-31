"""
Load and normalize data from the repo data/ folder or from multi-file uploads.
Supports DoorDash (FINANCIAL, MARKETING, OPERATIONS), Uber Eats, and Grubhub.
"""

import os
import io
import pandas as pd
from pathlib import Path
from typing import Optional, List, Dict, Any, Union

# -----------------------------------------------------------------------------
# Platform detection from column names (and optional filename)
# -----------------------------------------------------------------------------
def detect_platform_from_columns(columns: List[str], filename: str = "") -> str:
    """
    Label data as DoorDash, Grubhub, or Uber Eats from column names.
    - DoorDash: "DoorDash" in any column name, OR ("Store ID" in columns AND "Shop ID" not in columns)
    - Grubhub: "grubhub" in any column name (case-insensitive)
    - Else: Uber Eats
    """
    cols_str = " ".join(str(c) for c in columns).lower()
    col_lower = [str(c).strip().lower() for c in columns]
    name_lower = (filename or "").lower()
    if "doordash" in cols_str or "doordash" in name_lower:
        return "DoorDash"
    if "store id" in col_lower:
        if "shop id" not in col_lower:
            return "DoorDash"
    if "grubhub" in cols_str or "grubhub" in name_lower:
        return "Grubhub"
    return "Uber Eats"


def get_file_summary(
    file_or_path: Union[Any, str],
    store_content: bool = False,
) -> Optional[Dict[str, Any]]:
    """
    Peek a file: return dict with name, platform, columns, rows, size_bytes.
    If store_content=True (for uploads), also include "content" (bytes) for later use.
    """
    try:
        name = getattr(file_or_path, "name", None) or str(file_or_path)
        if hasattr(file_or_path, "getvalue"):
            content = file_or_path.getvalue()
            size = len(content)
            buf = io.BytesIO(content)
            is_excel = name.lower().endswith((".xlsx", ".xls"))
            df = pd.read_excel(buf) if is_excel else pd.read_csv(buf)
        else:
            path = Path(file_or_path)
            size = path.stat().st_size
            is_excel = path.suffix.lower() in (".xlsx", ".xls")
            df = pd.read_excel(path) if is_excel else pd.read_csv(path)
            name = path.name
        columns = list(df.columns)
        platform = detect_platform_from_columns(columns, name)
        out = {
            "name": name,
            "platform": platform,
            "columns": columns,
            "rows": len(df),
            "size_bytes": size,
        }
        if store_content and hasattr(file_or_path, "getvalue"):
            out["content"] = file_or_path.getvalue()
        elif store_content and isinstance(file_or_path, (str, Path)):
            out["path"] = str(file_or_path)
        return out
    except Exception:
        return None


def collect_review_from_uploads(uploaded_files: List[Any], store_content: bool = False) -> List[Dict[str, Any]]:
    """Build review list from uploaded files. Use store_content=True only if not passing upload_file_lookup to load_from_review_data (avoids duplicating large file bytes in session state)."""
    result = []
    for f in uploaded_files or []:
        summary = get_file_summary(f, store_content=store_content)
        if summary:
            result.append(summary)
    return result


def collect_review_from_data_folder(root: str = "data") -> List[Dict[str, Any]]:
    """Scan data/ folder and return review list (path stored, no content)."""
    root_path = Path(root)
    if not root_path.exists():
        return []
    result = []
    for p in sorted(root_path.rglob("*")):
        if not p.is_file() or p.suffix.lower() not in (".csv", ".xlsx", ".xls"):
            continue
        summary = get_file_summary(str(p), store_content=False)
        if summary:
            summary["path"] = str(p)
            result.append(summary)
    return result


def load_from_review_data(
    review_data: List[Dict[str, Any]],
    upload_file_lookup: Optional[List[Any]] = None,
) -> Dict[str, Any]:
    """
    Run load_from_uploads using reviewed files (with platform already set).
    review_data items have: name, platform, and either "content" (bytes), "path", or use upload_file_lookup.
    Pass upload_file_lookup (list of file-like with .name and .getvalue()) to avoid storing content in review_data (saves memory).
    """
    class BytesFile:
        def __init__(self, name: str, content: bytes):
            self.name = name
            self._content = content
        def getvalue(self):
            return self._content

    name_to_content = {}
    if upload_file_lookup:
        for f in upload_file_lookup or []:
            name = getattr(f, "name", None) or str(f)
            if hasattr(f, "getvalue"):
                name_to_content[name] = f.getvalue()

    dd_files = []
    ue_files = []
    gh_files = []
    for item in review_data or []:
        name = item.get("name", "")
        platform = item.get("platform", "Uber Eats")
        if "content" in item:
            wrapper = BytesFile(name, item["content"])
        elif "path" in item:
            wrapper = item["path"]
        elif name and name in name_to_content:
            wrapper = BytesFile(name, name_to_content[name])
        else:
            continue
        if platform == "DoorDash":
            dd_files.append(wrapper)
        elif platform == "Grubhub":
            gh_files.append(wrapper)
        else:
            ue_files.append(wrapper)
    return load_from_uploads(dd_files, ue_files, gh_files)

# -----------------------------------------------------------------------------
# Data folder discovery (for data/ in repo root)
# -----------------------------------------------------------------------------
def _discover_data_folder(root: str = "data"):
    """Find financial, marketing, and operations files under root."""
    root = Path(root)
    if not root.exists():
        return {}, [], [], [], [], []
    dd_financial_paths = []
    dd_marketing_paths = []
    dd_operations_paths = []
    ue_paths = []
    gh_financial_paths = []
    gh_operations_paths = []

    for p in root.rglob("*"):
        if not p.is_file() or p.suffix.lower() not in (".csv", ".xlsx", ".xls"):
            continue
        name = p.name.upper()
        rel = str(p.relative_to(root))
        # DoorDash: FINANCIAL_* (transaction), SALES_* (store-level aggregate), MARKETING_*, OPERATIONS_*
        if "FINANCIAL" in name and ("TRANSACTION" in name or "SIMPLIFIED" in name or "DETAILED" in name):
            dd_financial_paths.append(str(p))
        elif "SALES" in name and ("VIEWBYSTORE" in name or "AGGREGATE" in name):
            dd_financial_paths.append(str(p))
        elif "MARKETING" in name and ("PROMOTION" in name or "SPONSORED" in name):
            dd_marketing_paths.append(str(p))
        elif "OPERATIONS" in name or "CANCELLATION" in name or "DOWNTIME" in name or "MISSINGANDINCORRECT" in name or "MISSING_AND_INCORRECT" in name:
            dd_operations_paths.append(str(p))
        # Grubhub: sales report, financials.csv, or operations (GH_ or grubhub in path)
        elif ("grubhub" in rel.lower() or "GH_" in name) and ("SALES" in name or "financial" in p.name.lower() or "financials.csv" in p.name.lower()):
            gh_financial_paths.append(str(p))
        elif "operations-summary" in p.name.lower() or ("grubhub_store_id" in name and "total_orders" in name) or ("OPS" in name and ("grubhub" in rel.lower() or "GH_" in name)):
            gh_operations_paths.append(str(p))
        # Uber Eats: Order History, Payout, Inaccurate (incl. typo Inacurate), Downtime, Order Accuracy, Paused
        elif "ORDER HISTORY" in name or "PAYOUT" in name or "INACCURATE" in name or "INACURATE" in name or "DOWNTIME" in name or "ORDER ACCURACY" in name or "PAUSED" in name:
            ue_paths.append(str(p))
        elif "united_states" in p.name and p.suffix == ".csv":
            ue_paths.append(str(p))

    return dd_financial_paths, dd_marketing_paths, dd_operations_paths, ue_paths, gh_financial_paths, gh_operations_paths


def _read_csv_path_or_buffer(path_or_buffer):
    path_str = getattr(path_or_buffer, "name", None) or str(path_or_buffer)
    is_excel = path_str.lower().endswith((".xlsx", ".xls"))
    if hasattr(path_or_buffer, "getvalue"):
        buf = io.BytesIO(path_or_buffer.getvalue())
        return pd.read_excel(buf) if is_excel else pd.read_csv(buf)
    if hasattr(path_or_buffer, "read"):
        data = path_or_buffer.read()
        buf = io.BytesIO(data) if isinstance(data, bytes) else io.BytesIO(data.encode() if isinstance(data, str) else data)
        return pd.read_excel(buf) if is_excel else pd.read_csv(buf)
    return pd.read_excel(path_or_buffer) if is_excel else pd.read_csv(path_or_buffer)


def _ensure_date_col(df, date_columns=None):
    date_columns = date_columns or [
        "Timestamp local date", "Timestamp local time", "Order date", "Date", "order_date", "transaction_date",
        "Start Date", "Time Customer Ordered",
    ]
    for col in date_columns:
        if col in df.columns:
            df = df.copy()
            df["_date"] = pd.to_datetime(df[col], errors="coerce").dt.normalize()
            if df["_date"].notna().any():
                return df
    return None


# -----------------------------------------------------------------------------
# DoorDash loaders
# -----------------------------------------------------------------------------
def load_doordash_financial(path_or_buffer):
    """Load one DoorDash financial CSV (SIMPLIFIED or DETAILED) to common schema."""
    df = _read_csv_path_or_buffer(path_or_buffer)
    out = _ensure_date_col(df)
    if out is None:
        return None, "No date column found"
    if "Subtotal" not in out.columns:
        return None, "No Subtotal column"
    out["platform"] = "DoorDash"
    out["Store name"] = out.get("Store name", "Unknown")
    out["Transaction type"] = out.get("Transaction type", "Order")
    return out, None


def load_doordash_sales_aggregate(path_or_buffer):
    """
    Load DoorDash SALES_viewByStore_aggregate CSV (store-level).
    Expands to one row per order so dashboard gets order count + sales total.
    """
    df = _read_csv_path_or_buffer(path_or_buffer)
    # Columns: Start Date, End Date, Store Name, Store ID, Gross Sales, Total Delivered or Picked Up Orders, AOV, ...
    order_col = None
    for c in ["Total Delivered or Picked Up Orders", "Total Orders Including Cancelled Orders"]:
        if c in df.columns:
            order_col = c
            break
    if order_col is None:
        return None, "No order count column"
    sales_col = None
    for c in ["Gross Sales", "Gross sales"]:
        if c in df.columns:
            sales_col = c
            break
    if sales_col is None:
        return None, "No Gross Sales column"
    if "Start Date" not in df.columns:
        return None, "No Start Date column"
    df["_date"] = pd.to_datetime(df["Start Date"], errors="coerce").dt.normalize()
    df["Store name"] = df.get("Store Name", df.get("Store name", "Unknown"))
    df["platform"] = "DoorDash"
    df["Transaction type"] = "order"
    # Expand: one row per order, Subtotal = Gross Sales / orders for that store/period
    rows = []
    for _, r in df.iterrows():
        n = int(r[order_col]) if pd.notna(r[order_col]) else 0
        if n <= 0:
            continue
        sales = float(r[sales_col]) if pd.notna(r[sales_col]) else 0.0
        subtotal = sales / n
        d = r["_date"]
        for _ in range(n):
            rows.append({
                "_date": d,
                "Store name": r["Store name"],
                "Subtotal": subtotal,
                "platform": "DoorDash",
                "Transaction type": "order",
            })
    if not rows:
        return None, "No orders in file"
    out = pd.DataFrame(rows)
    return out, None


def load_doordash_marketing(path_or_buffer):
    """Load DoorDash marketing CSV (Promo or Sponsored)."""
    df = _read_csv_path_or_buffer(path_or_buffer)
    if "Date" not in df.columns:
        return None, "No Date column"
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.normalize()
    df["_date"] = df["Date"]
    return df, None


def load_doordash_operations_cancellations(path_or_buffer):
    """Load DoorDash operations cancellations CSV."""
    df = _read_csv_path_or_buffer(path_or_buffer)
    df["_date"] = pd.to_datetime(df.get("Start Date", df.get("End Date", pd.NaT)), errors="coerce").dt.normalize()
    return df, None


def load_doordash_operations_downtime(path_or_buffer):
    """Load DoorDash operations downtime CSV."""
    df = _read_csv_path_or_buffer(path_or_buffer)
    df["_date"] = pd.to_datetime(df.get("Start Date", df.get("End Date", pd.NaT)), errors="coerce").dt.normalize()
    return df, None


def load_doordash_operations_missing_incorrect(path_or_buffer):
    """Load DoorDash missing/incorrect orders CSV."""
    df = _read_csv_path_or_buffer(path_or_buffer)
    df["_date"] = pd.to_datetime(df.get("Start Date", df.get("End Date", pd.NaT)), errors="coerce").dt.normalize()
    return df, None


def load_doordash_from_paths(financial_paths, marketing_paths, operations_paths):
    """Load all DoorDash data from file paths. Returns dict with financial_df, promo_df, ads_df, operations."""
    financial_dfs = []
    sales_aggregate_dfs = []  # raw store-level aggregates (not expanded)
    promo_dfs = []
    ads_dfs = []
    ops_cancellations = []
    ops_downtime = []
    ops_missing_incorrect = []

    for p in financial_paths:
        try:
            p_str = str(p).upper()
            if "SALES" in p_str and ("VIEWBYSTORE" in p_str or "AGGREGATE" in p_str):
                # Keep the raw aggregate for the Sales tab
                raw_df = _read_csv_path_or_buffer(p)
                sales_aggregate_dfs.append(raw_df)
                df, err = load_doordash_sales_aggregate(p)
            else:
                df, err = load_doordash_financial(p)
            if err is None and df is not None:
                financial_dfs.append(df)
        except Exception:
            pass
    for p in marketing_paths:
        try:
            df, err = load_doordash_marketing(p)
            if err is None:
                if "SPONSORED" in str(p).upper() or "SPONSORED_LISTING" in str(p).upper():
                    ads_dfs.append(df)
                else:
                    promo_dfs.append(df)
        except Exception:
            pass
    for p in operations_paths:
        try:
            if "cancellation" in str(p).lower():
                df, _ = load_doordash_operations_cancellations(p)
                if df is not None:
                    ops_cancellations.append(df)
            elif "downtime" in str(p).lower():
                df, _ = load_doordash_operations_downtime(p)
                if df is not None:
                    ops_downtime.append(df)
            elif "missing" in str(p).lower() or "incorrect" in str(p).lower():
                df, _ = load_doordash_operations_missing_incorrect(p)
                if df is not None:
                    ops_missing_incorrect.append(df)
        except Exception:
            pass

    return {
        "financial_df": pd.concat(financial_dfs, ignore_index=True) if financial_dfs else None,
        "sales_aggregate_df": pd.concat(sales_aggregate_dfs, ignore_index=True) if sales_aggregate_dfs else None,
        "promo_df": pd.concat(promo_dfs, ignore_index=True) if promo_dfs else None,
        "ads_df": pd.concat(ads_dfs, ignore_index=True) if ads_dfs else None,
        "operations": {
            "cancellations": pd.concat(ops_cancellations, ignore_index=True) if ops_cancellations else None,
            "downtime": pd.concat(ops_downtime, ignore_index=True) if ops_downtime else None,
            "missing_incorrect": pd.concat(ops_missing_incorrect, ignore_index=True) if ops_missing_incorrect else None,
        },
    }


# -----------------------------------------------------------------------------
# Grubhub loaders (financials.csv style + operations-summary)
# -----------------------------------------------------------------------------
def load_grubhub_financial(path_or_buffer):
    """Load Grubhub financial CSV (order_channel, order_date, subtotal, store_name, etc.)."""
    df = _read_csv_path_or_buffer(path_or_buffer)
    # Normalize to common schema
    out = df.copy()
    for date_col in ["order_date", "transaction_date", "Order Date"]:
        if date_col in out.columns:
            out["_date"] = pd.to_datetime(out[date_col], errors="coerce").dt.normalize()
            break
    if "_date" not in out.columns and "Order Date" in out.columns:
        out["_date"] = pd.to_datetime(out["Order Date"], errors="coerce").dt.normalize()
    for amt_col in ["subtotal", "Subtotal", "merchant_net_total"]:
        if amt_col in out.columns:
            out["Subtotal"] = pd.to_numeric(out[amt_col], errors="coerce").fillna(0)
            break
    if "Subtotal" not in out.columns:
        return None, "No amount column"
    out["Store name"] = out.get("store_name", out.get("Store Name", "Unknown"))
    out["Transaction type"] = "Order"
    out["platform"] = "Grubhub"
    if "_date" not in out.columns:
        out["_date"] = pd.NaT
    return out, None


def load_grubhub_operations(path_or_buffer):
    """Load Grubhub operations summary CSV."""
    df = _read_csv_path_or_buffer(path_or_buffer)
    for date_col in ["week_start_date", "start_date", "Start Date", "End Date", "end_date"]:
        if date_col in df.columns:
            df["_date"] = pd.to_datetime(df[date_col], errors="coerce").dt.normalize()
            break
    else:
        df["_date"] = pd.NaT
    return df, None


def load_grubhub_from_paths(financial_paths, operations_paths):
    """Load Grubhub data from paths."""
    financial_dfs = []
    operations_dfs = []
    for p in financial_paths:
        try:
            df, err = load_grubhub_financial(p)
            if err is None:
                financial_dfs.append(df)
        except Exception:
            pass
    for p in operations_paths:
        try:
            df, _ = load_grubhub_operations(p)
            if df is not None:
                operations_dfs.append(df)
        except Exception:
            pass
    return {
        "financial_df": pd.concat(financial_dfs, ignore_index=True) if financial_dfs else None,
        "operations_df": pd.concat(operations_dfs, ignore_index=True) if operations_dfs else None,
    }


# -----------------------------------------------------------------------------
# Uber Eats loaders (inaccurate_orders, downtime, order_history, etc.)
# -----------------------------------------------------------------------------
def load_ubereats_file(path_or_buffer):
    """Load one Uber Eats CSV; normalize to a common shape if it's order/financial-like."""
    df = _read_csv_path_or_buffer(path_or_buffer)
    # Payout summary (aggregate): Order Count, Sales (excl. tax), Payout Date -> expand to one row per order
    if "Order Count" in df.columns and "Sales (excl. tax)" in df.columns:
        date_col = "Payout Date" if "Payout Date" in df.columns else None
        if not date_col:
            return df
        df["_date"] = pd.to_datetime(df[date_col], errors="coerce").dt.normalize()
        df["Store name"] = df.get("Store Name", "Unknown")
        df["platform"] = "Uber Eats"
        df["Transaction type"] = "Order"
        rows = []
        for _, r in df.iterrows():
            n = int(r["Order Count"]) if pd.notna(r["Order Count"]) else 0
            if n <= 0:
                continue
            sales = pd.to_numeric(r["Sales (excl. tax)"], errors="coerce") or 0.0
            subtotal = sales / n
            for _ in range(n):
                rows.append({
                    "_date": r["_date"],
                    "Store name": r["Store name"],
                    "Subtotal": subtotal,
                    "platform": "Uber Eats",
                    "Transaction type": "Order",
                })
        if rows:
            return pd.DataFrame(rows)
    # Detect type by columns
    if "Order ID" in df.columns and "Ticket Size" in df.columns:
        df["_date"] = pd.to_datetime(df.get("Time Customer Ordered", df.get("Time Merchant Accepted", pd.NaT)), errors="coerce").dt.normalize()
        df["Subtotal"] = pd.to_numeric(df.get("Ticket Size", 0), errors="coerce").fillna(0)
        df["Store name"] = df.get("Store", "Unknown")
        df["Transaction type"] = "Order"
        df["platform"] = "Uber Eats"
    elif "Date" in df.columns and "Restaurant Offline" in df.columns:
        df["_date"] = pd.to_datetime(df["Date"], errors="coerce").dt.normalize()
    elif "order_date" in df.columns or "order_number" in df.columns:
        for c in ["order_date", "Date", "date"]:
            if c in df.columns:
                df["_date"] = pd.to_datetime(df[c], errors="coerce").dt.normalize()
                break
    return df


def load_ubereats_from_paths(paths):
    """Load all Uber Eats CSVs; merge financial-like into one df, keep operations separate."""
    financial_dfs = []
    inaccurate_dfs = []
    downtime_dfs = []
    for p in paths:
        try:
            df = load_ubereats_file(p)
            # Check operations types FIRST (some have Ticket Size too)
            if "Order Issue" in df.columns or "Inaccurate Items" in df.columns or "Item Issue Details" in df.columns:
                if "Time Customer Ordered" in df.columns:
                    df["_date"] = pd.to_datetime(df["Time Customer Ordered"], errors="coerce").dt.normalize()
                inaccurate_dfs.append(df)
            elif "Pause Start" in df.columns or "Reason For Pausing" in df.columns:
                if "Pause Start" in df.columns:
                    df["_date"] = pd.to_datetime(df["Pause Start"], errors="coerce").dt.normalize()
                downtime_dfs.append(df)
            elif "Restaurant Offline" in df.columns or "Menu Available" in df.columns:
                downtime_dfs.append(df)
            elif "Subtotal" in df.columns or "Ticket Size" in df.columns:
                financial_dfs.append(df)
        except Exception:
            pass
    return {
        "financial_df": pd.concat(financial_dfs, ignore_index=True) if financial_dfs else None,
        "inaccurate_df": pd.concat(inaccurate_dfs, ignore_index=True) if inaccurate_dfs else None,
        "downtime_df": pd.concat(downtime_dfs, ignore_index=True) if downtime_dfs else None,
    }


# -----------------------------------------------------------------------------
# Load all from data/ folder
# -----------------------------------------------------------------------------
def load_all_from_data_folder(root: str = "data"):
    """
    Discover and load DoorDash, Uber Eats, and Grubhub data from the data/ folder.
    Returns dict: { "doordash": {...}, "uber_eats": {...}, "grubhub": {...} }
    """
    dd_fin, dd_mkt, dd_ops, ue_paths, gh_fin, gh_ops = _discover_data_folder(root)
    result = {}
    dd = load_doordash_from_paths(dd_fin, dd_mkt, dd_ops)
    if dd["financial_df"] is not None or dd["operations"]["cancellations"] is not None:
        result["doordash"] = dd
    ue = load_ubereats_from_paths(ue_paths)
    if ue["financial_df"] is not None or ue["inaccurate_df"] is not None:
        result["uber_eats"] = ue
    gh = load_grubhub_from_paths(gh_fin, gh_ops)
    if gh["financial_df"] is not None or gh["operations_df"] is not None:
        result["grubhub"] = gh
    return result


# -----------------------------------------------------------------------------
# Load from Streamlit multi-file uploads (list of UploadedFile)
# -----------------------------------------------------------------------------
def categorize_uploaded_files(files):
    """Split uploaded files into DoorDash (financial/marketing/operations), Uber Eats, Grubhub by filename."""
    dd_fin, dd_mkt, dd_ops, ue_files, gh_fin, gh_ops = [], [], [], [], [], []
    for f in files or []:
        name = (getattr(f, "name", None) or str(f)).upper()
        if "FINANCIAL" in name and ("TRANSACTION" in name or "SIMPLIFIED" in name or "DETAILED" in name):
            dd_fin.append(f)
        elif "SALES" in name and ("VIEWBYSTORE" in name or "AGGREGATE" in name):
            dd_fin.append(f)
        elif "MARKETING" in name and ("PROMOTION" in name or "SPONSORED" in name):
            dd_mkt.append(f)
        elif "OPERATIONS" in name or "CANCELLATION" in name or "DOWNTIME" in name or "MISSING" in name:
            dd_ops.append(f)
        elif "financials" in name.lower() or "grubhub" in name.lower():
            if "operations" in name.lower() or "summary" in name.lower():
                gh_ops.append(f)
            else:
                gh_fin.append(f)
        elif "inaccurate" in name or "order_accuracy" in name or "downtime" in name or "order_history" in name or "payout" in name or "paused" in name or "united_states" in name:
            ue_files.append(f)
        else:
            # Heuristic: try first line for Grubhub (order_channel) or Uber Eats (Store, Order ID)
            try:
                buf = f.getvalue() if hasattr(f, "getvalue") else open(f, "rb").read()
                first = buf.decode("utf-8", errors="ignore").split("\n")[0][:200]
                if "order_channel" in first or "grubhub_store_id" in first:
                    gh_fin.append(f) if "total_orders" not in first else gh_ops.append(f)
                elif "Store" in first and ("Order ID" in first or "Order Issue" in first):
                    ue_files.append(f)
            except Exception:
                pass
    return dd_fin, dd_mkt, dd_ops, ue_files, gh_fin, gh_ops


def load_from_uploads(dd_files, ue_files, gh_files):
    """
    Load from three lists of uploaded files (DoorDash, Uber Eats, Grubhub).
    Each list can contain multiple files. Returns same structure as load_all_from_data_folder.
    """
    result = {}
    dd_fin, dd_mkt, dd_ops = [], [], []
    for f in dd_files or []:
        name = (getattr(f, "name", None) or str(f)).upper()
        if "FINANCIAL" in name and ("TRANSACTION" in name or "SIMPLIFIED" in name or "DETAILED" in name):
            dd_fin.append(f)
        elif "SALES" in name and ("VIEWBYSTORE" in name or "AGGREGATE" in name):
            dd_fin.append(f)
        elif "MARKETING" in name:
            dd_mkt.append(f)
        elif "OPERATIONS" in name or "CANCELLATION" in name or "DOWNTIME" in name or "MISSING" in name:
            dd_ops.append(f)
        else:
            dd_fin.append(f)
    if dd_fin or dd_mkt or dd_ops:
        result["doordash"] = load_doordash_from_paths(dd_fin, dd_mkt, dd_ops)

    ue_data = load_ubereats_from_paths(ue_files or [])
    if ue_data["financial_df"] is not None or ue_data["inaccurate_df"] is not None or ue_data["downtime_df"] is not None:
        result["uber_eats"] = ue_data

    gh_fin_list = []
    gh_ops_list = []
    for f in gh_files or []:
        name = (getattr(f, "name", None) or str(f)).lower()
        if "operations" in name or "summary" in name:
            gh_ops_list.append(f)
        else:
            gh_fin_list.append(f)
    gh_data = load_grubhub_from_paths(gh_fin_list, gh_ops_list)
    if gh_data["financial_df"] is not None or gh_data["operations_df"] is not None:
        result["grubhub"] = gh_data

    return result
