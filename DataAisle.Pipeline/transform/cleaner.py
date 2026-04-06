# ============================================================
# DataAisle Pipeline — transform/cleaner.py
# Takes the raw string DataFrame from csv_reader and:
#   1. Strips whitespace from all string columns
#   2. Casts types (dates, numbers)
#   3. Drops fully empty rows
#   4. Flags and separates bad rows so they can be rejected
# Returns (clean_df, rejected_df)
# ============================================================

import logging
import pandas as pd

logger = logging.getLogger(__name__)


def clean(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Clean the raw ingested DataFrame.

    Returns
    -------
    (clean_df, rejected_df)
        clean_df    — rows that passed all checks, ready for transformation
        rejected_df — rows that failed, with a 'rejection_reason' column
    """
    df = df.copy()
    rejected_rows = []

    # ----------------------------------------------------------
    # 1. Strip whitespace from every string column
    # ----------------------------------------------------------
    str_cols = df.select_dtypes(include="object").columns
    df[str_cols] = df[str_cols].apply(lambda col: col.str.strip())

    # ----------------------------------------------------------
    # 2. Replace empty strings with NaN so we can detect nulls
    # ----------------------------------------------------------
    df.replace("", pd.NA, inplace=True)

    # ----------------------------------------------------------
    # 3. Drop completely empty rows
    # ----------------------------------------------------------
    before = len(df)
    df.dropna(how="all", inplace=True)
    dropped = before - len(df)
    if dropped:
        logger.info(f"Dropped {dropped} fully empty rows")

    # ----------------------------------------------------------
    # 4. Cast sale_date → datetime
    # ----------------------------------------------------------
    df, rejected_rows = _cast_dates(df, rejected_rows)

    # ----------------------------------------------------------
    # 5. Cast quantity → int, unit_price → float
    # ----------------------------------------------------------
    df, rejected_rows = _cast_numerics(df, rejected_rows)

    # ----------------------------------------------------------
    # 6. Validate business rules
    # ----------------------------------------------------------
    df, rejected_rows = _validate_business_rules(df, rejected_rows)

    # ----------------------------------------------------------
    # 7. Deduplicate (same date + sku + store = same sale)
    # ----------------------------------------------------------
    before = len(df)
    df.drop_duplicates(subset=["sale_date", "sku", "store_name"], inplace=True)
    dupes = before - len(df)
    if dupes:
        logger.info(f"Removed {dupes} duplicate rows")

    rejected_df = pd.DataFrame(rejected_rows) if rejected_rows else pd.DataFrame()

    logger.info(
        f"Cleaning complete — {len(df):,} clean rows, "
        f"{len(rejected_df):,} rejected rows"
    )
    return df.reset_index(drop=True), rejected_df


# ------------------------------------------------------------------
# Private helpers
# ------------------------------------------------------------------

def _cast_dates(
    df: pd.DataFrame, rejected: list
) -> tuple[pd.DataFrame, list]:
    mask_bad = pd.to_datetime(df["sale_date"], errors="coerce").isna()
    bad = df[mask_bad].copy()
    if not bad.empty:
        bad["rejection_reason"] = "invalid sale_date format"
        rejected.extend(bad.to_dict("records"))
        logger.warning(f"Rejected {len(bad)} rows — unparseable sale_date")

    df = df[~mask_bad].copy()
    df["sale_date"] = pd.to_datetime(df["sale_date"])
    return df, rejected


def _cast_numerics(
    df: pd.DataFrame, rejected: list
) -> tuple[pd.DataFrame, list]:
    # quantity
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")
    bad_qty = df[df["quantity"].isna()].copy()
    if not bad_qty.empty:
        bad_qty["rejection_reason"] = "invalid quantity — not a number"
        rejected.extend(bad_qty.to_dict("records"))
    df = df[df["quantity"].notna()].copy()
    df["quantity"] = df["quantity"].astype(int)

    # unit_price
    df["unit_price"] = pd.to_numeric(df["unit_price"], errors="coerce")
    bad_price = df[df["unit_price"].isna()].copy()
    if not bad_price.empty:
        bad_price["rejection_reason"] = "invalid unit_price — not a number"
        rejected.extend(bad_price.to_dict("records"))
    df = df[df["unit_price"].notna()].copy()
    df["unit_price"] = df["unit_price"].astype(float)

    return df, rejected


def _validate_business_rules(
    df: pd.DataFrame, rejected: list
) -> tuple[pd.DataFrame, list]:
    # quantity must be > 0
    bad = df[df["quantity"] <= 0].copy()
    if not bad.empty:
        bad["rejection_reason"] = "quantity must be > 0"
        rejected.extend(bad.to_dict("records"))
    df = df[df["quantity"] > 0].copy()

    # unit_price must be >= 0
    bad = df[df["unit_price"] < 0].copy()
    if not bad.empty:
        bad["rejection_reason"] = "unit_price cannot be negative"
        rejected.extend(bad.to_dict("records"))
    df = df[df["unit_price"] >= 0].copy()

    # Required string fields must not be null
    required_str = ["sku", "product_name", "store_name", "supplier_name"]
    for col in required_str:
        bad = df[df[col].isna()].copy()
        if not bad.empty:
            bad["rejection_reason"] = f"missing required field: {col}"
            rejected.extend(bad.to_dict("records"))
        df = df[df[col].notna()].copy()

    return df, rejected
