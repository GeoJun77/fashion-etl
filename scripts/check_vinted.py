# scripts/check_vinted.py
# Manual smoke test of the Vinted API : fetches a few products and prints them.
# Calls the real API — not part of the test suite.
#
#   python -m scripts.check_vinted

from src.scrapers.vinted_scraper import VintedScraper
from src.transformers.cleaner import Cleaner


def main() -> None:
    raw = VintedScraper().run(max_products=10)
    clean = Cleaner().clean(raw)

    print(f"\n{len(clean)} products\n")
    for p in clean:
        print(f"{p.title} — {p.brand} — {p.price}€ — {p.category} — {', '.join(p.sizes)}")
        print(f"    {p.url}")


if __name__ == "__main__":
    main()
