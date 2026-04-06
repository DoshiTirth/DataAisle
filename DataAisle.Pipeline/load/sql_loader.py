# ============================================================
# DataAisle Pipeline — load/sql_loader.py
# Handles all writes to SQL Server:
#   - Opens/closes etl_pipeline_runs records
#   - Bulk inserts fact_sales in batches
#   - Writes rejected rows to etl_rejected_rows
# ============================================================

import json
import logging
import pyodbc
import pandas as pd
from datetime import datetime, timezone
from config import RAW_CONNECTION_STRING, BATCH_SIZE, PIPELINE_NAME

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Pipeline run lifecycle
# ------------------------------------------------------------------

def start_pipeline_run(source_file: str) -> int:
    """
    Insert a new row into etl_pipeline_runs with status='running'.
    Returns the new run_id.
    """
    conn = pyodbc.connect(RAW_CONNECTION_STRING)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO dbo.etl_pipeline_runs
                (pipeline_name, source_file, start_time, status)
            OUTPUT INSERTED.run_id
            VALUES (?, ?, ?, 'running')
            """,
            PIPELINE_NAME,
            source_file,
            datetime.now(timezone.utc),
        )
        run_id = cursor.fetchone()[0]
        conn.commit()
        logger.info(f"Pipeline run started — run_id={run_id}")
        return run_id
    finally:
        conn.close()


def finish_pipeline_run(
    run_id: int,
    rows_ingested: int,
    rows_failed: int,
    success: bool,
    error_message: str | None = None,
) -> None:
    """Update etl_pipeline_runs with final status and row counts."""
    conn = pyodbc.connect(RAW_CONNECTION_STRING)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE dbo.etl_pipeline_runs
            SET end_time      = ?,
                status        = ?,
                rows_ingested = ?,
                rows_failed   = ?,
                error_message = ?
            WHERE run_id = ?
            """,
            datetime.now(timezone.utc),
            "success" if success else "failed",
            rows_ingested,
            rows_failed,
            error_message,
            run_id,
        )
        conn.commit()
        logger.info(
            f"Pipeline run finished — run_id={run_id} "
            f"status={'success' if success else 'failed'} "
            f"ingested={rows_ingested:,} failed={rows_failed:,}"
        )
    finally:
        conn.close()


# ------------------------------------------------------------------
# Fact table loader
# ------------------------------------------------------------------

def load_fact_sales(df: pd.DataFrame) -> int:
    """
    Bulk insert rows into fact_sales in batches.

    Parameters
    ----------
    df : DataFrame with columns matching fact_sales
         (date_id, product_id, store_id, supplier_id,
          quantity, unit_price, total_amount)

    Returns
    -------
    int — number of rows successfully inserted
    """
    if df.empty:
        logger.warning("load_fact_sales called with empty DataFrame — nothing to load")
        return 0

    conn = pyodbc.connect(RAW_CONNECTION_STRING)
    total_inserted = 0

    try:
        cursor = conn.cursor()
        cursor.fast_executemany = True  # big speed boost for bulk inserts

        rows = list(df.itertuples(index=False, name=None))

        for i in range(0, len(rows), BATCH_SIZE):
            batch = rows[i : i + BATCH_SIZE]
            cursor.executemany(
                """
                INSERT INTO dbo.fact_sales
                    (date_id, product_id, store_id, supplier_id,
                     quantity, unit_price, total_amount)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                batch,
            )
            conn.commit()
            total_inserted += len(batch)
            logger.info(
                f"Inserted batch {i // BATCH_SIZE + 1} "
                f"({total_inserted:,}/{len(rows):,} rows)"
            )

        return total_inserted

    finally:
        conn.close()


# ------------------------------------------------------------------
# Rejected rows writer
# ------------------------------------------------------------------

def save_rejected_rows(rejected_df: pd.DataFrame, run_id: int) -> int:
    """
    Write rejected rows to etl_rejected_rows as JSON blobs.
    Returns the number of rows saved.
    """
    if rejected_df.empty:
        return 0

    conn = pyodbc.connect(RAW_CONNECTION_STRING)
    try:
        cursor = conn.cursor()
        records = []
        for _, row in rejected_df.iterrows():
            reason = str(row.get("rejection_reason", "unknown"))
            raw = row.drop(labels=["rejection_reason"], errors="ignore").to_dict()
            # Convert non-serialisable types (Timestamps, etc.)
            raw_json = json.dumps(raw, default=str)
            records.append((run_id, raw_json, reason))

        cursor.executemany(
            """
            INSERT INTO dbo.etl_rejected_rows (run_id, source_row, rejection_reason)
            VALUES (?, ?, ?)
            """,
            records,
        )
        conn.commit()
        logger.info(f"Saved {len(records):,} rejected rows to etl_rejected_rows")
        return len(records)
    finally:
        conn.close()
