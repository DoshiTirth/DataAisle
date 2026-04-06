# ============================================================
# DataAisle Pipeline — transform/dimension_mapper.py
# Takes the clean DataFrame and resolves every dimension:
#   - dim_product  (upsert by SKU)
#   - dim_store    (upsert by name + city)
#   - dim_supplier (upsert by name)
#   - dim_date     (lookup by YYYYMMDD integer key)
# Returns a DataFrame ready to load into fact_sales.
# ============================================================

import logging
import pandas as pd
import pyodbc
from config import RAW_CONNECTION_STRING

logger = logging.getLogger(__name__)


def map_dimensions(df: pd.DataFrame) -> pd.DataFrame:
    """
    Resolve all foreign key IDs and compute total_amount.

    Returns
    -------
    pd.DataFrame with columns:
        date_id, product_id, store_id, supplier_id,
        quantity, unit_price, total_amount
    """
    conn = pyodbc.connect(RAW_CONNECTION_STRING)
    try:
        product_map  = _upsert_products(df, conn)
        store_map    = _upsert_stores(df, conn)
        supplier_map = _upsert_suppliers(df, conn)
        _ensure_dates(df, conn)

        conn.commit()

        # ----------------------------------------------------------
        # Build the fact rows
        # ----------------------------------------------------------
        fact = df[["sale_date", "sku", "store_name", "supplier_name",
                   "quantity", "unit_price"]].copy()

        fact["date_id"]     = fact["sale_date"].dt.strftime("%Y%m%d").astype(int)
        fact["product_id"]  = fact["sku"].map(product_map)
        fact["store_id"]    = fact["store_name"].map(store_map)
        fact["supplier_id"] = fact["supplier_name"].map(supplier_map)
        fact["total_amount"] = (
            fact["quantity"] * fact["unit_price"]
        ).round(2)

        # Drop rows where any FK lookup failed (shouldn't happen, but safety net)
        before = len(fact)
        fact.dropna(subset=["date_id", "product_id", "store_id", "supplier_id"],
                    inplace=True)
        dropped = before - len(fact)
        if dropped:
            logger.warning(f"Dropped {dropped} rows — FK lookup returned None")

        result = fact[[
            "date_id", "product_id", "store_id", "supplier_id",
            "quantity", "unit_price", "total_amount"
        ]].reset_index(drop=True)

        logger.info(f"Dimension mapping complete — {len(result):,} fact rows ready")
        return result

    finally:
        conn.close()


# ------------------------------------------------------------------
# Private upsert helpers
# Each returns a dict:  natural_key → surrogate_id
# ------------------------------------------------------------------

def _upsert_products(df: pd.DataFrame, conn: pyodbc.Connection) -> dict:
    """Insert new products, return sku → product_id map."""
    cursor = conn.cursor()
    unique = df[["sku", "product_name", "category", "brand"]].drop_duplicates("sku")

    for _, row in unique.iterrows():
        cursor.execute("""
            IF NOT EXISTS (SELECT 1 FROM dbo.dim_product WHERE sku = ?)
                INSERT INTO dbo.dim_product (sku, name, category, brand)
                VALUES (?, ?, ?, ?)
        """, row.sku, row.sku, row.product_name, row.category, row.brand)

    cursor.execute("SELECT sku, product_id FROM dbo.dim_product")
    mapping = {r[0]: r[1] for r in cursor.fetchall()}
    logger.info(f"Products in dim: {len(mapping)}")
    return mapping


def _upsert_stores(df: pd.DataFrame, conn: pyodbc.Connection) -> dict:
    """Insert new stores, return store_name → store_id map."""
    cursor = conn.cursor()
    unique = df[["store_name", "city", "region"]].drop_duplicates("store_name")

    for _, row in unique.iterrows():
        cursor.execute("""
            IF NOT EXISTS (SELECT 1 FROM dbo.dim_store WHERE name = ?)
                INSERT INTO dbo.dim_store (name, city, region)
                VALUES (?, ?, ?)
        """, row.store_name, row.store_name, row.city, row.region)

    cursor.execute("SELECT name, store_id FROM dbo.dim_store")
    mapping = {r[0]: r[1] for r in cursor.fetchall()}
    logger.info(f"Stores in dim: {len(mapping)}")
    return mapping


def _upsert_suppliers(df: pd.DataFrame, conn: pyodbc.Connection) -> dict:
    """Insert new suppliers, return supplier_name → supplier_id map."""
    cursor = conn.cursor()
    unique = df[["supplier_name", "supplier_country"]].drop_duplicates("supplier_name")

    for _, row in unique.iterrows():
        cursor.execute("""
            IF NOT EXISTS (SELECT 1 FROM dbo.dim_supplier WHERE name = ?)
                INSERT INTO dbo.dim_supplier (name, country)
                VALUES (?, ?)
        """, row.supplier_name, row.supplier_name, row.supplier_country)

    cursor.execute("SELECT name, supplier_id FROM dbo.dim_supplier")
    mapping = {r[0]: r[1] for r in cursor.fetchall()}
    logger.info(f"Suppliers in dim: {len(mapping)}")
    return mapping


def _ensure_dates(df: pd.DataFrame, conn: pyodbc.Connection) -> None:
    """Insert any missing dates into dim_date."""
    cursor = conn.cursor()
    unique_dates = df["sale_date"].dt.normalize().unique()

    for d in unique_dates:
        ts = pd.Timestamp(d)
        date_id = int(ts.strftime("%Y%m%d"))
        cursor.execute("""
            IF NOT EXISTS (SELECT 1 FROM dbo.dim_date WHERE date_id = ?)
                INSERT INTO dbo.dim_date
                    (date_id, full_date, day, month, quarter, year,
                     day_name, month_name, is_weekend)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            date_id,
            date_id,
            ts.date(),
            ts.day,
            ts.month,
            (ts.month - 1) // 3 + 1,
            ts.year,
            ts.day_name(),
            ts.month_name(),
            1 if ts.dayofweek >= 5 else 0,
        )
