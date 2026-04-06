# ============================================================
# DataAisle Pipeline — ingest/csv_reader.py
# Reads a raw sales CSV file and returns a clean DataFrame.
# No transformation happens here — just loading and basic typing.
# ============================================================

import logging
import pandas as pd
from pathlib import Path

logger = logging.getLogger(__name__)

# Columns we expect in every sales CSV
REQUIRED_COLUMNS = {
    "sale_date",
    "sku",
    "product_name",
    "category",
    "brand",
    "store_name",
    "city",
    "region",
    "supplier_name",
    "supplier_country",
    "quantity",
    "unit_price",
}


def read_csv(filepath: str | Path) -> pd.DataFrame:
    """
    Read a sales CSV file into a DataFrame.

    Returns
    -------
    pd.DataFrame
        Raw DataFrame — no transformation applied yet.

    Raises
    ------
    FileNotFoundError  : if the file does not exist
    ValueError         : if required columns are missing
    """
    filepath = Path(filepath)

    if not filepath.exists():
        raise FileNotFoundError(f"CSV not found: {filepath}")

    logger.info(f"Reading CSV: {filepath.name}")

    df = pd.read_csv(
        filepath,
        dtype=str,          # read everything as string — cleaner.py handles types
        keep_default_na=False,  # don't auto-convert empty strings to NaN yet
        encoding="utf-8",
    )

    # Normalise column names: lowercase, strip whitespace, replace spaces with _
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(r"\s+", "_", regex=True)
    )

    _validate_columns(df, filepath.name)

    logger.info(f"Loaded {len(df):,} rows from {filepath.name}")
    return df


def _validate_columns(df: pd.DataFrame, filename: str) -> None:
    """Raise ValueError if any required column is missing."""
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(
            f"{filename} is missing required columns: {sorted(missing)}"
        )
