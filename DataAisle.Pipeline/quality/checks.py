# DataAisle Pipeline — quality/checks.py
# Runs data quality checks on the clean DataFrame and logs
# each result to etl_data_quality_log in SQL Server.

import logging
import pyodbc
import pandas as pd
from config import RAW_CONNECTION_STRING

logger = logging.getLogger(__name__)


def run_checks(df: pd.DataFrame, run_id: int) -> bool:
    """
    Run all data quality checks against the clean DataFrame.
    Logs every check result to etl_data_quality_log.

    Parameters
    ----------
    df     : clean DataFrame (post-cleaner, pre-loader)
    run_id : the current pipeline run ID (FK to etl_pipeline_runs)

    Returns
    -------
    bool — True if all checks passed, False if any failed
    """
    checks = [
        _check_no_null_skus,
        _check_no_null_store,
        _check_positive_quantity,
        _check_positive_price,
        _check_total_row_count,
        _check_date_range,
    ]

    all_passed = True
    results = []

    for check_fn in checks:
        passed, check_name, failed_count, message = check_fn(df)
        if not passed:
            all_passed = False
            logger.warning(f"Quality check FAILED: {check_name} — {message}")
        else:
            logger.info(f"Quality check passed: {check_name}")

        results.append((run_id, check_name, passed, failed_count, message))

    _log_results(results)
    return all_passed

# Individual checks
# Each returns: (passed: bool, name: str, failed_count: int, message: str)

def _check_no_null_skus(df: pd.DataFrame):
    failed = df["sku"].isna().sum()
    return (
        failed == 0,
        "null_check_sku",
        int(failed),
        f"{failed} rows have null SKU" if failed else "All SKUs present",
    )


def _check_no_null_store(df: pd.DataFrame):
    failed = df["store_name"].isna().sum()
    return (
        failed == 0,
        "null_check_store_name",
        int(failed),
        f"{failed} rows have null store_name" if failed else "All store names present",
    )


def _check_positive_quantity(df: pd.DataFrame):
    failed = (df["quantity"] <= 0).sum()
    return (
        failed == 0,
        "range_check_quantity",
        int(failed),
        f"{failed} rows have quantity <= 0" if failed else "All quantities positive",
    )


def _check_positive_price(df: pd.DataFrame):
    failed = (df["unit_price"] < 0).sum()
    return (
        failed == 0,
        "range_check_unit_price",
        int(failed),
        f"{failed} rows have negative unit_price" if failed else "All prices non-negative",
    )


def _check_total_row_count(df: pd.DataFrame):
    count = len(df)
    passed = count > 0
    return (
        passed,
        "row_count_check",
        0 if passed else 1,
        f"{count:,} rows in dataset" if passed else "Dataset is empty",
    )


def _check_date_range(df: pd.DataFrame):
    if "sale_date" not in df.columns:
        return (False, "date_range_check", 1, "sale_date column missing")

    min_date = df["sale_date"].min()
    max_date = df["sale_date"].max()
    future_rows = (df["sale_date"] > pd.Timestamp.today()).sum()

    passed = future_rows == 0
    return (
        passed,
        "date_range_check",
        int(future_rows),
        f"Dates: {min_date.date()} → {max_date.date()}. "
        f"{future_rows} future-dated rows." if future_rows
        else f"Dates: {min_date.date()} → {max_date.date()}. All valid.",
    )


# Write results to etl_data_quality_log

def _log_results(results: list) -> None:
    conn = pyodbc.connect(RAW_CONNECTION_STRING)
    try:
        cursor = conn.cursor()
        cursor.executemany(
            """
            INSERT INTO dbo.etl_data_quality_log
                (run_id, check_name, passed, failed_count, message)
            VALUES (?, ?, ?, ?, ?)
            """,
            [(run_id, name, int(passed), count, msg)
             for run_id, name, passed, count, msg in results],
        )
        conn.commit()
        logger.info(f"Logged {len(results)} quality check results to DB")
    finally:
        conn.close()
