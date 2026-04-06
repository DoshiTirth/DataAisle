# DataAisle Pipeline — ingest/api_reader.py
# Fetches product enrichment data from Open Food Facts API.
# Used to enrich dim_product with extra category/brand info.

import logging
import time
import requests
import pandas as pd
from config import OPENFOODFACTS_URL, API_PAGE_SIZE

logger = logging.getLogger(__name__)

# How long to wait between API calls (be polite to the free API)
REQUEST_DELAY_SECONDS = 0.5


def fetch_products(category: str, max_pages: int = 3) -> pd.DataFrame:
    """
    Fetch products from Open Food Facts for a given category.

    Parameters
    ----------
    category  : e.g. 'beverages', 'snacks', 'dairy'
    max_pages : number of pages to fetch (each page = API_PAGE_SIZE rows)

    Returns
    -------
    pd.DataFrame with columns: sku, name, category, brand
    """
    records = []

    for page in range(1, max_pages + 1):
        logger.info(f"Fetching Open Food Facts: category={category} page={page}")
        try:
            resp = requests.get(
                OPENFOODFACTS_URL,
                params={
                    "categories_tags": category,
                    "fields": "code,product_name,brands,categories_tags",
                    "page_size": API_PAGE_SIZE,
                    "page": page,
                },
                headers={
                    "User-Agent": "DataAisle/1.0 (data engineering portfolio project)"
                },
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()

            products = data.get("products", [])
            if not products:
                logger.info(f"No more products at page {page}, stopping.")
                break

            for p in products:
                code = p.get("code", "").strip()
                name = p.get("product_name", "").strip()
                brand = p.get("brands", "Unknown").strip().split(",")[0]
                if code and name:
                    records.append({
                        "sku":      code[:50],
                        "name":     name[:150],
                        "category": category.replace("-", " ").title(),
                        "brand":    brand[:80] if brand else "Unknown",
                    })

            time.sleep(REQUEST_DELAY_SECONDS)

        except requests.RequestException as e:
            logger.warning(f"API request failed (page {page}): {e}")
            break

    if not records:
        logger.warning(f"No products fetched for category: {category}")
        return pd.DataFrame(columns=["sku", "name", "category", "brand"])

    df = pd.DataFrame(records).drop_duplicates(subset=["sku"])
    logger.info(f"Fetched {len(df)} unique products for category '{category}'")
    return df
