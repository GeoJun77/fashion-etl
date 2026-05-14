# tests/test_awin.py
# Tests the Awin scraper with real feed data — checks both Sneakin and Kastner & Ohler

import io
import zipfile

import requests
import pandas as pd

from config.settings import settings
from src.scrapers.awin_scraper import AwinScraper


if not settings.awin_feed_url:
    print("ERROR : AWIN_FEED_URL is not set in .env")
    exit(1)

# --- Step 1 : Check all merchants in the feed ---
print("Step 1 : Checking merchants in feed...")
response = requests.get(
    settings.awin_feed_url,
    timeout=120,
    headers={"User-Agent": "Mozilla/5.0"},
)
print(f"Feed size : {len(response.content) / 1024 / 1024:.1f} MB")

merchants = {}
with zipfile.ZipFile(io.BytesIO(response.content)) as z:
    csv_filename = [f for f in z.namelist() if f.endswith(".csv")][0]
    with z.open(csv_filename) as f:
        for chunk in pd.read_csv(
            f,
            sep=";",
            chunksize=5000,
            low_memory=False,
            dtype=str,
            on_bad_lines="skip",
        ):
            for _, row in chunk[["merchant_id", "merchant_name"]].drop_duplicates().iterrows():
                mid = str(row["merchant_id"]).strip()
                mname = str(row["merchant_name"]).strip()
                if mid not in merchants:
                    merchants[mid] = mname

print(f"\nMerchants found : {len(merchants)}")
for mid, mname in merchants.items():
    print(f"  ID={mid} — {mname}")

# --- Step 2 : Run the scraper ---
print("\nStep 2 : Running scraper (max=10)...")
scraper = AwinScraper(feed_url=settings.awin_feed_url)
products = scraper.run(max_products=10)

print(f"\nProducts collected : {len(products)}")
print()

for p in products:
    print("---")
    print(f"Title    : {p.title}")
    print(f"Brand    : {p.brand}")
    print(f"Price    : {p.price_raw} {p.currency}")
    print(f"Category : {p.category_raw}")
    print(f"Source   : {p.source}")
    print(f"Colors   : {p.colors}")
    print(f"Sizes    : {p.sizes}")
    print(f"Material : {p.extra['material']}")
    print(f"In stock : {p.extra['in_stock']}")

# --- Step 3 : Check source distribution ---
print("\nStep 3 : Source distribution in collected products")
sources = {}
for p in products:
    sources[p.source] = sources.get(p.source, 0) + 1
for source, count in sources.items():
    print(f"  {source} : {count} products")