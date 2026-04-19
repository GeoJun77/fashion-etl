# src/scrapers/zalando_scraper.py
# Scraper for Zalando — extracts products from listing pages

from typing import Iterator
from loguru import logger
from src.scrapers.base_scraper import BaseScraper, RawProduct


class ZalandoScraper(BaseScraper):
    """
    Scrapes Zalando FR listing pages.
    Targets multiple categories : women, men, girls and boys.
    """

    # Category pages to scrape
    CATEGORIES = [
        # Women — tops
        {"url": "https://www.zalando.fr/robes-femme/",              "label": "women dresses"},
        {"url": "https://www.zalando.fr/tops-femme/",               "label": "women tops"},
        {"url": "https://www.zalando.fr/blouses-tuniques-femme/",   "label": "women blouses"},
        {"url": "https://www.zalando.fr/t-shirts-femme/",           "label": "women t-shirts"},
        {"url": "https://www.zalando.fr/pulls-gilets-femme/",       "label": "women knitwear"},

        # Women — bottoms
        {"url": "https://www.zalando.fr/jeans-femme/",              "label": "women jeans"},
        {"url": "https://www.zalando.fr/pantalons-femme/",          "label": "women trousers"},
        {"url": "https://www.zalando.fr/jupes-femme/",              "label": "women skirts"},
        {"url": "https://www.zalando.fr/shorts-femme/",             "label": "women shorts"},

        # Women — outerwear
        {"url": "https://www.zalando.fr/manteaux-vestes-femme/",    "label": "women coats"},
        {"url": "https://www.zalando.fr/vestes-blazers-femme/",     "label": "women blazers"},

        # Women — shoes
        {"url": "https://www.zalando.fr/sneakers-femme/",           "label": "women sneakers"},
        {"url": "https://www.zalando.fr/escarpins-femme/",          "label": "women heels"},
        {"url": "https://www.zalando.fr/bottes-bottines-femme/",    "label": "women boots"},
        {"url": "https://www.zalando.fr/sandales-femme/",           "label": "women sandals"},

        # Women — accessories
        {"url": "https://www.zalando.fr/sacs-femme/",               "label": "women bags"},
        {"url": "https://www.zalando.fr/bijoux-femme/",             "label": "women jewelry"},

        # Men — tops
        {"url": "https://www.zalando.fr/t-shirts-homme/",           "label": "men t-shirts"},
        {"url": "https://www.zalando.fr/chemises-homme/",           "label": "men shirts"},
        {"url": "https://www.zalando.fr/pulls-gilets-homme/",       "label": "men knitwear"},

        # Men — bottoms
        {"url": "https://www.zalando.fr/jeans-homme/",              "label": "men jeans"},
        {"url": "https://www.zalando.fr/pantalons-homme/",          "label": "men trousers"},
        {"url": "https://www.zalando.fr/shorts-homme/",             "label": "men shorts"},

        # Men — outerwear
        {"url": "https://www.zalando.fr/manteaux-vestes-homme/",    "label": "men coats"},
        {"url": "https://www.zalando.fr/vestes-blazers-homme/",     "label": "men blazers"},

        # Men — shoes
        {"url": "https://www.zalando.fr/sneakers-homme/",           "label": "men sneakers"},
        {"url": "https://www.zalando.fr/boots-bottines-homme/",     "label": "men boots"},

        # Men — accessories
        {"url": "https://www.zalando.fr/sacs-homme/",               "label": "men bags"},

        # Girls — tops
        {"url": "https://www.zalando.fr/robes-fille/",              "label": "girls dresses"},
        {"url": "https://www.zalando.fr/tops-fille/",               "label": "girls tops"},
        {"url": "https://www.zalando.fr/t-shirts-fille/",           "label": "girls t-shirts"},
        {"url": "https://www.zalando.fr/pulls-gilets-fille/",       "label": "girls knitwear"},

        # Girls — bottoms
        {"url": "https://www.zalando.fr/jeans-fille/",              "label": "girls jeans"},
        {"url": "https://www.zalando.fr/jupes-fille/",              "label": "girls skirts"},
        {"url": "https://www.zalando.fr/pantalons-fille/",          "label": "girls trousers"},
        {"url": "https://www.zalando.fr/shorts-fille/",             "label": "girls shorts"},

        # Girls — outerwear
        {"url": "https://www.zalando.fr/manteaux-vestes-fille/",    "label": "girls coats"},

        # Girls — shoes
        {"url": "https://www.zalando.fr/sneakers-fille/",           "label": "girls sneakers"},
        {"url": "https://www.zalando.fr/bottes-bottines-fille/",    "label": "girls boots"},
        {"url": "https://www.zalando.fr/sandales-fille/",           "label": "girls sandals"},

        # Boys — tops
        {"url": "https://www.zalando.fr/t-shirts-garcon/",          "label": "boys t-shirts"},
        {"url": "https://www.zalando.fr/chemises-garcon/",          "label": "boys shirts"},
        {"url": "https://www.zalando.fr/pulls-gilets-garcon/",      "label": "boys knitwear"},

        # Boys — bottoms
        {"url": "https://www.zalando.fr/jeans-garcon/",             "label": "boys jeans"},
        {"url": "https://www.zalando.fr/pantalons-garcon/",         "label": "boys trousers"},
        {"url": "https://www.zalando.fr/shorts-garcon/",            "label": "boys shorts"},

        # Boys — outerwear
        {"url": "https://www.zalando.fr/manteaux-vestes-garcon/",   "label": "boys coats"},

        # Boys — shoes
        {"url": "https://www.zalando.fr/sneakers-garcon/",          "label": "boys sneakers"},
        {"url": "https://www.zalando.fr/bottes-bottines-garcon/",   "label": "boys boots"},
    ]

    def __init__(self):
        super().__init__("zalando")

    def scrape(self, max_products: int) -> Iterator[RawProduct]:
        """Scrapes all configured categories until max_products is reached."""
        collected = 0

        for category in self.CATEGORIES:
            if collected >= max_products:
                break

            logger.info(f"[Zalando] Scraping category : {category['label']}")
            soup = self.get(category["url"])

            if not soup:
                logger.warning(f"[Zalando] Could not fetch : {category['url']}")
                continue

            # Find all product articles on the page
            articles = soup.find_all("article")
            logger.info(f"[Zalando] Found {len(articles)} articles on page")

            for article in articles:
                if collected >= max_products:
                    break

                product = self._parse_article(article, category["label"])
                if product:
                    yield product
                    collected += 1

    def _parse_article(self, article, category_label: str) -> RawProduct | None:
        """Extracts product data from a single article HTML element."""
        try:
            # Extract title
            title_el = article.find("h3")
            if not title_el:
                return None
            title = title_el.get_text(strip=True)

            # Extract URL
            link_el = article.find("a", href=True)
            if not link_el:
                return None
            url = link_el["href"]
            if not url.startswith("http"):
                url = f"https://www.zalando.fr{url}"

            # Extract price
            price_el = article.find(attrs={"data-testid": "price"})
            price_raw = price_el.get_text(strip=True) if price_el else ""

            # Extract brand
            brand_el = article.find("h4")
            brand = brand_el.get_text(strip=True) if brand_el else ""

            # Extract image
            img_el = article.find("img")
            image_url = img_el.get("src", "") if img_el else ""

            if not title:
                return None

            return RawProduct(
                source="zalando",
                url=url,
                title=title,
                price_raw=price_raw,
                category_raw=category_label,
                brand=brand,
                image_url=image_url,
            )

        except Exception as e:
            logger.debug(f"[Zalando] Article skipped : {e}")
            return None