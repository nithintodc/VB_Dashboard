# Data File Mapping — Sales, Marketing, Operations

This document maps each file in your `data/` folder (or uploaded folder) to **what it provides** and **which tag/category** the app uses for analysis.

---

## How this mapping works

1. **Sales** = order counts, revenue (AOV, gross sales, subtotals), payouts, commissions. Used for: Orders, AOV, date range, platform totals.
2. **Marketing** = promotions, discounts, sponsored listings, ROAS, ad spend. Used for: Promo ROAS, Ads ROAS, marketing metrics.
3. **Operations** = cancellations, downtime, missing/incorrect orders, wait times, quality. Used for: Cancellations %, Inaccurate %, Downtime, Wait time.

Each file is tagged with one or more of: `sales` | `marketing` | `operations`, and with a short description of key columns and how the app uses it.

---

## DoorDash (DD)

### Sales

| File (pattern) | Tag | Key columns | What it gives |
|----------------|-----|-------------|----------------|
| **DD Sales Report - Store Level** / `SALES_viewByStore_aggregate_*.csv` | **sales** | `Start Date`, `End Date`, `Store Name`, `Store ID`, `Gross Sales`, `Total Orders Including Cancelled Orders`, `Total Delivered or Picked Up Orders`, `AOV`, `Total Commission`, `Total Promotion Fees`, `Total Ad Fees` | Store-level sales aggregate: orders, gross sales, AOV, commission, promo/ad fees. Primary DoorDash **sales** source for dashboard. |

- **Use for:** Orders, AOV, sales totals, date range.  
- **Note:** Row per store per date range; no transaction-level detail. For order-level dates we’d need a transaction export; this file is store-level aggregate.

---

### Marketing

| File (pattern) | Tag | Key columns | What it gives |
|----------------|-----|-------------|----------------|
| **DD Marketing Feb** / `MARKETING_PROMOTION_*.csv` | **marketing** | `Date`, `Campaign name`, `Type of promotion`, `Store name`, `Orders`, `Sales`, `Customer discounts from marketing`, `Marketing fees`, `Average order value`, **`ROAS`** | Promotions / order discounts: orders, sales, spend, **Promo ROAS**. |
| **DD Marketing Feb** / `MARKETING_SPONSORED_LISTING_*.csv` | **marketing** | `Date`, `Campaign name`, `Store name`, `Impressions`, `Clicks`, `Orders`, `Sales`, `Marketing fees`, `Average order value`, **`ROAS`** | Sponsored listing (ads): impressions, clicks, orders, sales, **Ads ROAS**. |

- **Use for:** Promo ROAS, Ads ROAS, marketing metrics in Overall/Monthly/Weekly/Daywise.

---

### Operations

| File (pattern) | Tag | Key columns | What it gives |
|----------------|-----|-------------|----------------|
| **DD Ops Report Feb** / `OPERATIONS_QUALITY_viewByStore_cancellations_*.csv` | **operations** | `Start Date`, `End Date`, `Store ID`, `Store Name`, `Cancellation Category - Short`, `Cancellation Category - Description`, **`Count of Orders`** | Store-level cancellation counts by category (avoidable store ops, item out of stock, store closed, etc.). |
| **DD Ops Report Feb** / `OPERATIONS_QUALITY_viewByStore_downtime_*.csv` | **operations** | `Start Date`, `End Date`, `Store ID`, `Store Name`, `Downtime Category - Short`, **`Minutes Downtime`** | Store-level downtime minutes (auto-pause, store closure, etc.). |
| **DD Ops Report Feb** / `OPERATIONS_QUALITY_viewByStore_missingAndIncorrect_*.csv` | **operations** | `Start Date`, `End Date`, `Store ID`, `Store Name`, `Error Category`, **`Count of Item Errors`**, `% of Total Item Errors` | Store-level missing/incorrect item error counts. |
| **DD Ops Report Feb** / `OPERATIONS_QUALITY_viewByStore_aggregate_*.csv` | **operations** | `Start Date`, `End Date`, `Store Name`, `Store ID`, `Total Orders Including Cancelled Orders`, `Total Delivered or Picked Up Orders`, `Total Missing or Incorrect Orders`, `Missing/Incorrect %`, `Total Cancelled Orders`, `Total Cancellation Rate %`, `Total Downtime in Minutes`, `Average Avoidable Dasher Wait`, `Average Dasher Wait`, `Uptime %`, `Downtime %` | One row per store: cancellations, missing/incorrect, downtime mins, wait times, uptime. **Best single DD operations summary.** |
| **DD Ops Order Level Feb** / `operations_quality_cancelled_orders_default_*.csv` | **operations** | `Order Placed Date`, `Order Placed Time`, `DD Order ID`, `Store Name`, `Cancelled at timestamp`, `Cancellation Category - Short`, `Order Subtotal` | Order-level cancelled orders; optional for cancellation detail. |
| **DD Ops Order Level Feb** / `operations_quality_missing_incorrect_orders_default_*.csv` | **operations** | `Order Delivered Date`, `DD Order ID`, `Store Name`, `Error Category`, `Item Name`, **`Error Charge`** | Order-level missing/incorrect items and error charges. |
| **DD Ops Order Level Feb** / `operations_quality_avoidable_wait_orders_default_*.csv` | **operations** | `Order Delivered Date`, `DD Order ID`, `Store Name`, `Avoidable Wait Time`, `Total Delivery Time (ASAP Time)`, `Order Subtotal` | Order-level **wait time** (avoidable wait, delivery time). |

- **Use for:** Cancellations %, Inaccurate %, Downtime, Wait time (and operations section in the app).

---

## Uber Eats (UE)

### Sales

| File (pattern) | Tag | Key columns | What it gives |
|----------------|-----|-------------|----------------|
| **UE Payout summary Feb.csv** | **sales** | `Store Name`, `Shop ID`, `Order Count`, `Sales (excl. tax)`, `Sales (incl. tax)`, `Total Sales after Adjustments (incl tax)`, `Total payout`, **`Payout Date`** | Payout-level sales: order count, sales, adjustments, payout date. Good for **sales** and date range by payout. |
| **UE Order History Feb.csv** | **sales** | `Store`, `Order ID`, `Order Status`, `Ticket Size`, **`Date Ordered`**, `Time Customer Ordered`, `Courier Wait Time (Restaurant)`, `Total Prep & Handoff Time`, `Order Duration` | Order-level: **Ticket Size** (AOV proxy), **Date Ordered**, status, wait/delivery times. Primary UE **sales** + optional wait time. |

- **Use for:** Orders, AOV (Ticket Size), date range; Order History also gives wait/prep time for operations.

---

### Marketing

| File (pattern) | Tag | Key columns | What it gives |
|----------------|-----|-------------|----------------|
| *(No UE marketing files in current sample)* | — | — | If you add Uber Eats promo/ads exports (e.g. with ROAS or spend), tag as **marketing**. |

---

### Operations

| File (pattern) | Tag | Key columns | What it gives |
|----------------|-----|-------------|----------------|
| **UE Inacurate Orders Feb.csv** | **operations** | `Store`, `Order ID`, `Time Customer Ordered`, `Order Issue`, `Item Issue Details`, `Inaccurate Items`, `Ticket Size`, `Customer Refunded`, `Refund Covered by Merchant` | Order-level **inaccurate orders**: issue type, items, refunds. |
| **UE Paused Details Feb.csv** | **operations** | `Store`, `City`, **`Pause Start`**, **`Pause Duration`**, `Reason For Pausing` | Store **downtime**: when and how long store was paused. |
| **UE Order Accuracy Feb.xlsx** | **operations** (supplementary) | Sheets: summary of inaccurate orders, top items, store leaderboard, "Issue Type Raw Data". Multi-row headers, report style. | Summary/report view of inaccurate orders; **UE Inacurate Orders Feb.csv** is the main raw source. |

- **Use for:** Inaccurate %, Downtime (paused duration); Order History can supplement wait time.

---

## Grubhub (GH)

### Sales

| File (pattern) | Tag | Key columns | What it gives |
|----------------|-----|-------------|----------------|
| **GH_Sales_Report_Feb_.csv** | **sales** | **`week_start_date`**, `grubhub_store_id`, `store_name`, **`total_orders`**, **`subtotal_sales`**, `merchant_total`, `commission`, `merchant_net_total` | Weekly store-level **sales**: orders, subtotal, net. Primary GH **sales** source. |

- **Use for:** Orders, AOV (subtotal_sales/total_orders), date range (week_start_date).

---

### Marketing

| File (pattern) | Tag | Key columns | What it gives |
|----------------|-----|-------------|----------------|
| *(No GH marketing files in current sample)* | — | — | If you add Grubhub promo/ads exports, tag as **marketing**. |

---

### Operations

| File (pattern) | Tag | Key columns | What it gives |
|----------------|-----|-------------|----------------|
| **GH_-_Ops_Reports_Feb_.csv** | **operations** | **`week_start_date`**, `grubhub_store_id`, `store_name`, **`total_orders`**, **`total_canceled_orders`**, `total_canceled_orders_rate`, `avoidable_canceled_orders`, **`avg_driver_time_at_store`**, **`avg_avoidable_driver_wait_time`**, `avg_order_to_delivery_time`, `ratings_all`, `reviews` | Weekly store-level: **cancellations**, **wait time** (driver at store, avoidable wait), delivery time, ratings. |

- **Use for:** Cancellations %, Wait time, optional ratings.

---

## Summary: which file to select for what

| Need | DoorDash | Uber Eats | Grubhub |
|------|----------|-----------|---------|
| **Sales (orders, AOV, date range)** | `SALES_viewByStore_aggregate_*.csv` | `UE Order History Feb.csv` and/or `UE Payout summary Feb.csv` | `GH_Sales_Report_Feb_.csv` |
| **Marketing (Promo ROAS)** | `MARKETING_PROMOTION_*.csv` | *(none in sample)* | *(none in sample)* |
| **Marketing (Ads ROAS)** | `MARKETING_SPONSORED_LISTING_*.csv` | *(none in sample)* | *(none in sample)* |
| **Operations (cancellations)** | `OPERATIONS_QUALITY_viewByStore_cancellations_*.csv` or aggregate | *(from Order History status)* | `GH_-_Ops_Reports_Feb_.csv` |
| **Operations (downtime)** | `OPERATIONS_QUALITY_viewByStore_downtime_*.csv` or aggregate | `UE Paused Details Feb.csv` | — |
| **Operations (missing/incorrect)** | `OPERATIONS_QUALITY_viewByStore_missingAndIncorrect_*.csv` or order-level | `UE Inacurate Orders Feb.csv` | — |
| **Operations (wait time)** | `operations_quality_avoidable_wait_orders_default_*.csv` or aggregate | `UE Order History Feb.csv` (Courier Wait Time, etc.) | `GH_-_Ops_Reports_Feb_.csv` |

---

## Store ID mapping (Airtable — Nithin's view)

The app can compare store IDs in your data files with a central mapping in Airtable ([Nithin's view](https://airtable.com/appmSjXVMWR99duPQ/tblub3DbzKIrfh4UA/viwBofuDyDvgxnXaJ)):

| Platform   | Data file column(s)     | Airtable column   |
|-----------|--------------------------|-------------------|
| DoorDash  | `Store ID`               | Doordash StoreID  |
| Grubhub   | `grubhub_store_id`       | Grubhub CID       |
| Uber Eats | `Shop ID`, `External Store ID` | UberEats UUID |

After **Review data**, a **Store ID matching matrix** shows per file: store IDs in data, in Airtable, only in data, only in Airtable, and matched. Set `AIRTABLE_PAT` (and optionally `AIRTABLE_STORE_MAPPING_BASE_ID`, `AIRTABLE_STORE_MAPPING_TABLE_ID`, `AIRTABLE_STORE_MAPPING_VIEW_ID`) to use this.

**If the matrix shows nothing or fails:** (1) Set `AIRTABLE_PAT` in `.env`. (2) Confirm base/table/view IDs point to Nithin's view. (3) Ensure the Airtable table has columns like *Doordash StoreID*, *Grubhub CID*, *UberEats UUID*. (4) Use the **Debug: Store mapping steps** expander to see at which step it failed (PAT, fetch, columns, or per-file match).

---

## How the app uses this

- **Discovery:** The app discovers files by path/name patterns (e.g. `FINANCIAL`, `MARKETING`, `OPERATIONS`, `SALES`, `grubhub`, `UE`, etc.) and infers platform (DoorDash vs Uber Eats vs Grubhub).
- **Tagging in code:** In `data_loader.py`, files are routed by filename/keywords into:
  - **Sales/financial:** financial_df (orders, AOV, date range)
  - **Marketing:** promo_df (Promo ROAS), ads_df (Ads ROAS)
  - **Operations:** cancellations, downtime, missing_incorrect (and for UE: inaccurate_df, downtime_df from Paused Details)
- This mapping document is the **source of truth** for what each file provides; the app’s heuristics are kept in sync with this so the right file is selected for sales, marketing, and operations.
