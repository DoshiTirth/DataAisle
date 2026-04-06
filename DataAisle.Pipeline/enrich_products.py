# DataAisle Pipeline — enrich_products.py
# Second data source: Open Food Facts API
# Enriches dim_product with real product data from the API,
# inserting any products not already in the dimension table.
#
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import argparse
import logging
import sys
import pyodbc
import pandas as pd

from config import RAW_CONNECTION_STRING
import importlib.util
spec = importlib.util.spec_from_file_location("api_reader", 
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "ingest", "api_reader.py"))
api_reader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api_reader)
fetch_products = api_reader.fetch_products

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("dataaisle.enrich")

DEFAULT_CATEGORIES = [
    "beverages",
    "snacks",
    "dairy",
    "cereals",
    "frozen-foods",
]


def enrich(categories: list[str]) -> int:
    """
    Fetch products from Open Food Facts and upsert into dim_product.
    Returns number of new products inserted.
    """
    all_products: list[pd.DataFrame] = []

    for cat in categories:
        logger.info(f"Fetching category: {cat}")
        df = fetch_products(cat, max_pages=2)
        if not df.empty:
            all_products.append(df)

    if not all_products:
        logger.warning("No products fetched from API")
        return 0

    combined = pd.concat(all_products, ignore_index=True)
    combined.drop_duplicates(subset=["sku"], inplace=True)
    logger.info(f"Total unique products from API: {len(combined)}")

    inserted = 0
    conn = pyodbc.connect(RAW_CONNECTION_STRING)
    try:
        cursor = conn.cursor()
        for _, row in combined.iterrows():
            cursor.execute("""
                IF NOT EXISTS (SELECT 1 FROM dbo.dim_product WHERE sku = ?)
                BEGIN
                    INSERT INTO dbo.dim_product (sku, name, category, brand)
                    VALUES (?, ?, ?, ?)
                    SELECT @@ROWCOUNT
                END
                ELSE
                    SELECT 0
            """, row.sku, row.sku, row.name, row.category, row.brand)
            result = cursor.fetchone()
            if result and result[0] == 1:
                inserted += 1

        conn.commit()
        logger.info(f"Inserted {inserted} new products into dim_product")
        return inserted

    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Enrich dim_product from Open Food Facts")
    parser.add_argument(
        "--categories",
        nargs="+",
        default=DEFAULT_CATEGORIES,
        help="List of Open Food Facts categories to fetch",
    )
    args = parser.parse_args()

    logger.info(f"Enriching products from categories: {args.categories}")
    count = enrich(args.categories)
    logger.info(f"Enrichment complete — {count} new products added")
