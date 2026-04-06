# DataAisle Pipeline — config.py
# All connection strings, paths, and pipeline settings live here.

import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()  # reads .env file if present

# Paths
BASE_DIR   = Path(__file__).parent
DATA_DIR   = BASE_DIR / "data"           # drop CSV files here
LOG_DIR    = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
# SQL Server connection
# Uses Windows Authentication (no username/password needed
# since SQL Server Express is running locally).
SQL_SERVER = os.getenv("DA_SQL_SERVER", r"(localdb)\MSSQLLocalDB")
SQL_DATABASE = os.getenv("DA_SQL_DATABASE", "DataAisle")

# pyodbc connection string — Windows Auth
CONNECTION_STRING = (
    f"mssql+pyodbc://@{SQL_SERVER}/{SQL_DATABASE}"
    f"?driver=ODBC+Driver+17+for+SQL+Server"
    f"&trusted_connection=yes"
)

# Raw pyodbc string (used for bulk inserts)
RAW_CONNECTION_STRING = (
    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
    f"SERVER={SQL_SERVER};"
    f"DATABASE={SQL_DATABASE};"
    f"Trusted_Connection=yes;"
)

# Pipeline settings
PIPELINE_NAME        = "DataAisle_CSV_Pipeline"
BATCH_SIZE           = 500      # rows per bulk insert batch
DATE_SPINE_START     = "2022-01-01"
DATE_SPINE_END       = "2026-12-31"

# API settings (Open Food Facts — free, no key needed)
OPENFOODFACTS_URL    = "https://world.openfoodfacts.org/api/v2/search"
API_PAGE_SIZE        = 20
