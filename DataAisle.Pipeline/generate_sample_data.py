# DataAisle Pipeline — generate_sample_data.py
# Generates a realistic fake sales CSV using the Faker library.
# Run this once to create test data before running main.py.
#
# Usage:
#   python generate_sample_data.py
#   python generate_sample_data.py --rows 5000 --output data/sales_large.csv

import argparse
import random
from pathlib import Path
from datetime import date, timedelta

import pandas as pd
from faker import Faker

fake = Faker("en_CA")   # Canadian locale — fits our default store country
random.seed(42)
Faker.seed(42)

# ------------------------------------------------------------------
# Master reference data — keeps the CSV internally consistent
# ------------------------------------------------------------------

PRODUCTS = [
    ("SKU-001", "Organic Whole Milk 2L",       "Dairy",      "Natrel"),
    ("SKU-002", "Sourdough Bread 750g",         "Bakery",     "ACE Bakery"),
    ("SKU-003", "Free Range Eggs 12pk",         "Dairy",      "Burnbrae Farms"),
    ("SKU-004", "Cold Brew Coffee 330ml",       "Beverages",  "Pilot Coffee"),
    ("SKU-005", "Greek Yogurt 500g",            "Dairy",      "Olympic"),
    ("SKU-006", "Atlantic Salmon Fillet 400g",  "Seafood",    "Ocean Choice"),
    ("SKU-007", "Baby Spinach 142g",            "Produce",    "Earthbound Farm"),
    ("SKU-008", "Aged Cheddar 400g",            "Dairy",      "Black Diamond"),
    ("SKU-009", "Sparkling Water 6pk",          "Beverages",  "San Pellegrino"),
    ("SKU-010", "Dark Chocolate 85g",           "Snacks",     "Lindt"),
    ("SKU-011", "Almond Butter 500g",           "Pantry",     "Maranatha"),
    ("SKU-012", "Frozen Edamame 400g",          "Frozen",     "President's Choice"),
    ("SKU-013", "Oat Milk 1L",                  "Beverages",  "Oatly"),
    ("SKU-014", "Avocado each",                 "Produce",    "Fresh Direct"),
    ("SKU-015", "Rotisserie Chicken",           "Deli",       "In-store"),
]

STORES = [
    ("FreshMart Downtown",  "Toronto",   "Ontario"),
    ("GreenGrocer Midtown", "Toronto",   "Ontario"),
    ("FreshMart Westside",  "Vancouver", "British Columbia"),
    ("Metro Fresh",         "Montreal",  "Quebec"),
    ("Prairie Pantry",      "Calgary",   "Alberta"),
    ("FreshMart Uptown",    "Ottawa",    "Ontario"),
]

SUPPLIERS = [
    ("Maple Leaf Foods",   "Canada"),
    ("Sysco Canada",       "Canada"),
    ("Gordon Food Service","Canada"),
    ("Lantic Inc",         "Canada"),
    ("Premium Brands",     "Canada"),
]

UNIT_PRICES = {sku: round(random.uniform(1.99, 24.99), 2) for sku, *_ in PRODUCTS}

# Inject ~3% bad rows for quality-check testing
BAD_ROW_RATE = 0.03


def random_date(start: date, end: date) -> date:
    return start + timedelta(days=random.randint(0, (end - start).days))


def make_row(bad: bool = False) -> dict:
    sku, name, category, brand = random.choice(PRODUCTS)
    store_name, city, region  = random.choice(STORES)
    supplier_name, sup_country = random.choice(SUPPLIERS)
    sale_date = random_date(date(2023, 1, 1), date(2025, 12, 31))

    row = {
        "sale_date":        sale_date.isoformat(),
        "sku":              sku,
        "product_name":     name,
        "category":         category,
        "brand":            brand,
        "store_name":       store_name,
        "city":             city,
        "region":           region,
        "supplier_name":    supplier_name,
        "supplier_country": sup_country,
        "quantity":         random.randint(1, 50),
        "unit_price":       UNIT_PRICES[sku],
    }

    if bad:
        flaw = random.choice(["bad_date", "bad_qty", "bad_price", "null_sku"])
        if flaw == "bad_date":
            row["sale_date"] = "not-a-date"
        elif flaw == "bad_qty":
            row["quantity"] = -random.randint(1, 10)
        elif flaw == "bad_price":
            row["unit_price"] = -abs(row["unit_price"])
        elif flaw == "null_sku":
            row["sku"] = ""

    return row


def generate(num_rows: int, output_path: Path) -> None:
    rows = []
    for i in range(num_rows):
        bad = random.random() < BAD_ROW_RATE
        rows.append(make_row(bad=bad))

    df = pd.DataFrame(rows)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)

    bad_count = sum(
        1 for r in rows
        if r["sale_date"] == "not-a-date"
        or r["quantity"] < 0
        or r["unit_price"] < 0
        or r["sku"] == ""
    )
    print(f"Generated {num_rows:,} rows  ({bad_count} intentionally bad)")
    print(f"Saved to: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows",   type=int,  default=2000)
    parser.add_argument("--output", type=Path, default=Path("data/sales.csv"))
    args = parser.parse_args()
    generate(args.rows, args.output)
