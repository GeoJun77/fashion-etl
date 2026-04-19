# tests/test_cleaner.py
# Tests the Cleaner with mock data

from src.scrapers.mock_scraper import MockScraper
from src.transformers.cleaner import Cleaner

# Generate 10 mock products
scraper = MockScraper()
raw_products = scraper.run(max_products=10)

# Clean them
cleaner = Cleaner()
clean_products = cleaner.clean(raw_products)

print(f"\nRaw products    : {len(raw_products)}")
print(f"Clean products  : {len(clean_products)}")
print()

for p in clean_products[:3]:
    print("---")
    print(f"Title     : {p.title}")
    print(f"Slug      : {p.slug}")
    print(f"Brand     : {p.brand}")
    print(f"Price     : {p.price} EUR")
    print(f"Promo     : {p.is_promotional} (original: {p.price_original})")
    print(f"Category  : {p.category}")
    print(f"Material  : {p.material}")
    print(f"Season    : {p.season}")
    print(f"Trends    : {p.trend_keywords}")
    print(f"Sizes     : {p.sizes}")
    print(f"Colors    : {p.colors}")