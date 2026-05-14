# tests/test_vinted.py
# Tests the Vinted scraper with real API data

from src.scrapers.vinted_scraper import VintedScraper

scraper = VintedScraper()
products = scraper.run(max_products=10)

print(f"\nProducts collected : {len(products)}")
print()

for p in products:
    print("---")
    print(f"Title    : {p.title}")
    print(f"Brand    : {p.brand}")
    print(f"Price    : {p.price_raw} EUR")
    print(f"Category : {p.category_raw}")
    print(f"Size     : {p.sizes}")
    print(f"URL      : {p.url}")