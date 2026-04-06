# ============================================================
# DataAisle Pipeline — main.py
# Orchestrates the full ETL pipeline:
#   1. Ingest  → read CSV file
#   2. Clean   → type cast, validate, reject bad rows
#   3. Quality → run checks, log to DB
#   4. Map     → resolve dimension FK IDs
#   5. Load    → bulk insert into fact_sales
#
# Usage:
#   python main.py                         # processes all CSVs in data/
#   python main.py --file data/sales.csv   # processes one specific file
# ============================================================

import argparse
import logging
import sys
from pathlib import Path

from config import DATA_DIR, LOG_DIR
from ingest.csv_reader import read_csv
from transform.cleaner import clean
from transform.dimension_mapper import map_dimensions
from quality.checks import run_checks
from load.sql_loader import (
    start_pipeline_run,
    finish_pipeline_run,
    load_fact_sales,
    save_rejected_rows,
)

# ------------------------------------------------------------------
# Logging setup — writes to console AND a daily log file
# ------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_DIR / "pipeline.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("dataaisle.main")


def run_pipeline(csv_path: Path) -> bool:
    """
    Run the full ETL pipeline for a single CSV file.
    Returns True on success, False on failure.
    """
    logger.info(f"{'=' * 55}")
    logger.info(f"Starting pipeline for: {csv_path.name}")
    logger.info(f"{'=' * 55}")

    run_id = start_pipeline_run(str(csv_path))

    try:
        # ----------------------------------------------------------
        # Step 1 — Ingest
        # ----------------------------------------------------------
        logger.info("Step 1/5 — Ingesting CSV")
        raw_df = read_csv(csv_path)

        # ----------------------------------------------------------
        # Step 2 — Clean
        # ----------------------------------------------------------
        logger.info("Step 2/5 — Cleaning data")
        clean_df, rejected_df = clean(raw_df)

        # Save rejected rows immediately
        rows_failed = save_rejected_rows(rejected_df, run_id)

        if clean_df.empty:
            raise ValueError("No clean rows remaining after cleaning step")

        # ----------------------------------------------------------
        # Step 3 — Quality checks
        # ----------------------------------------------------------
        logger.info("Step 3/5 — Running quality checks")
        checks_passed = run_checks(clean_df, run_id)
        if not checks_passed:
            logger.warning("Some quality checks failed — pipeline will continue "
                           "but results are flagged in etl_data_quality_log")

        # ----------------------------------------------------------
        # Step 4 — Dimension mapping
        # ----------------------------------------------------------
        logger.info("Step 4/5 — Mapping dimensions")
        fact_df = map_dimensions(clean_df)

        # ----------------------------------------------------------
        # Step 5 — Load
        # ----------------------------------------------------------
        logger.info("Step 5/5 — Loading fact_sales")
        rows_loaded = load_fact_sales(fact_df)

        finish_pipeline_run(
            run_id=run_id,
            rows_ingested=rows_loaded,
            rows_failed=rows_failed,
            success=True,
        )

        logger.info(
            f"Pipeline complete — "
            f"loaded={rows_loaded:,}  rejected={rows_failed:,}"
        )
        return True

    except Exception as exc:
        logger.exception(f"Pipeline FAILED: {exc}")
        finish_pipeline_run(
            run_id=run_id,
            rows_ingested=0,
            rows_failed=0,
            success=False,
            error_message=str(exc)[:2000],
        )
        return False


def main():
    parser = argparse.ArgumentParser(description="DataAisle ETL Pipeline")
    parser.add_argument(
        "--file",
        type=Path,
        default=None,
        help="Path to a specific CSV file. If omitted, processes all CSVs in data/",
    )
    parser.add_argument(
        "--enrich",
        action="store_true",
        help="Enrich dim_product from Open Food Facts API after loading",
    )
    args = parser.parse_args()

    if args.file:
        files = [args.file]
    else:
        files = sorted(DATA_DIR.glob("*.csv"))
        if not files:
            logger.error(f"No CSV files found in {DATA_DIR}")
            sys.exit(1)

    logger.info(f"Found {len(files)} CSV file(s) to process")

    success_count = 0
    for csv_file in files:
        ok = run_pipeline(csv_file)
        if ok:
            success_count += 1

    logger.info(
        f"All done — {success_count}/{len(files)} pipelines succeeded"
    )

    if getattr(args, 'enrich', False):
        logger.info("Running product enrichment from Open Food Facts API...")
        try:
            from enrich_products import enrich
            count = enrich(["beverages", "snacks", "dairy"])
            logger.info(f"Enrichment complete — {count} new products added")
        except Exception as e:
            logger.warning(f"Enrichment failed (non-critical): {e}")

    if success_count < len(files):
        sys.exit(1)


if __name__ == "__main__":
    main()
