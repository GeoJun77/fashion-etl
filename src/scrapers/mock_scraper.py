# src/scrapers/mock_scraper.py
# Generates realistic mock product data for testing the pipeline

import random
from datetime import datetime, timezone
from typing import Iterator

from src.scrapers.base_scraper import BaseScraper, RawProduct


class MockScraper(BaseScraper):
    """
    Generates realistic mock fashion products.
    Used for testing the pipeline while waiting for Awin API approvals.
    Includes : brands, sizes, materials, seasonal trends, descriptions.
    """

    SOURCES = [
        "shein", "hugo_boss", "lacoste", "guess", "etam",
        "jd_sports", "foot_locker", "benetton", "karl_lagerfeld",
        "pretty_little_thing", "boohoo", "yours_grandes_tailles",
        "cdiscount", "ms_mode", "cecil_mode", "street_one",
        "ulla_popken", "tezenis", "hunkemoller", "lululemon",
        "geox", "sneakin", "noukies", "prive_by_zalando",
        "adidas", "3_suisses", "intimissimi", "the_bradery",
        "yesstyle", "strellson", "kastner_ohler",
    ]

    CATEGORIES = [
        "women dresses", "women tops", "women jeans", "women coats",
        "women sneakers", "women bags", "women skirts", "women blouses",
        "women knitwear", "women blazers", "women heels", "women boots",
        "women sandals", "women jewelry", "women shorts", "women trousers",
        "men t-shirts", "men jeans", "men sneakers", "men coats",
        "men shirts", "men knitwear", "men blazers", "men trousers",
        "men boots", "men bags", "men shorts",
        "girls dresses", "girls tops", "girls jeans", "girls coats",
        "girls sneakers", "girls skirts", "girls boots",
        "boys t-shirts", "boys shirts", "boys jeans", "boys coats",
        "boys sneakers", "boys shorts",
    ]

    # --- Brands by segment ---
    LUXURY_BRANDS = [
        "Karl Lagerfeld", "Jacquemus", "Isabel Marant", "Ami Paris",
        "Sandro", "Maje", "Ba&sh", "IRO Paris", "The Kooples",
        "Rouje", "Ganni", "A.P.C", "Maison Kitsune", "Officine Generale",
        "Sezane", "Claudie Pierlot", "Zadig & Voltaire", "Vanessa Bruno",
        "Paul & Joe", "Carven", "Agnes b.", "Longchamp",
    ]

    PREMIUM_BRANDS = [
        "Hugo Boss", "Lacoste", "Guess", "Calvin Klein", "Tommy Hilfiger",
        "Ralph Lauren", "Comptoir des Cotonniers", "Caroll", "Gerard Darel",
        "Ted Baker", "Reiss", "Whistles", "Scotch & Soda", "Pepe Jeans",
        "G-Star RAW", "Diesel", "Armani Exchange", "BOSS Orange",
        "Barbour", "Hackett", "Faconnable",
    ]

    MID_BRANDS = [
        "Zara", "Mango", "H&M", "Uniqlo", "Cos", "Arket",
        "& Other Stories", "Monki", "Weekday", "Bershka",
        "Pull & Bear", "Stradivarius", "Massimo Dutti",
        "Promod", "Pimkie", "Morgan", "Naf Naf", "Camaieu",
        "Esprit", "Kookai", "Grain de Malice", "Jolie Jolie",
        "Gemo", "La Halle", "Kiabi", "Jennyfer", "Jules",
        "Celio", "Brice", "Bizzbee",
    ]

    FAST_FASHION_BRANDS = [
        "SHEIN", "Boohoo", "PrettyLittleThing", "Missguided",
        "Fashion Nova", "Romwe", "Zaful", "Nasty Gal",
        "ASOS Design", "Primark", "Oh Polly", "I Saw It First",
        "Rebellious Fashion", "Misspap",
    ]

    SPORT_BRANDS = [
        "Nike", "Adidas", "Puma", "New Balance", "Reebok",
        "Under Armour", "Lululemon", "Gymshark", "Fila",
        "Ellesse", "Champion", "Kappa", "Umbro", "Le Coq Sportif",
        "Salomon", "Columbia", "The North Face", "Patagonia",
        "Arc'teryx", "Hoka", "On Running", "Asics", "Saucony",
        "Brooks", "Mizuno", "Decathlon", "Quechua", "Domyos",
    ]

    STREETWEAR_BRANDS = [
        "Supreme", "Off-White", "Palm Angels", "Stussy", "Carhartt WIP",
        "A Bathing Ape", "Kith", "Noah", "Palace", "Vans",
        "Converse", "Dickies", "Wrangler", "Levi's", "Lee",
        "Tommy Jeans", "Calvin Klein Jeans", "Moschino Jeans",
    ]

    KIDS_BRANDS = [
        "Noukies", "Petit Bateau", "Bonpoint", "Jacadi",
        "Absorba", "Catimini", "Sergent Major", "Orchestra",
        "Du Pareil au Meme", "Okaidi", "Tape a l'Oeil",
        "Cyrillus", "Vertbaudet", "Bout'chou", "Bonton",
        "Burberry Kids", "Gucci Kids", "Moncler Enfant",
    ]

    # --- Sizes by category ---
    SIZES = {
        "women":       ["XS", "S", "M", "L", "XL", "XXL"],
        "women_shoes": ["35", "36", "37", "38", "39", "40", "41"],
        "men":         ["XS", "S", "M", "L", "XL", "XXL", "XXXL"],
        "men_jeans":   ["28/30", "30/30", "30/32", "32/30", "32/32",
                        "34/30", "34/32", "36/32"],
        "men_shoes":   ["39", "40", "41", "42", "43", "44", "45", "46"],
        "girls":       ["2Y", "3Y", "4Y", "5Y", "6Y", "8Y", "10Y", "12Y", "14Y"],
        "boys":        ["2Y", "3Y", "4Y", "5Y", "6Y", "8Y", "10Y", "12Y", "14Y"],
        "one_size":    ["One size"],
        "plus_size":   ["44", "46", "48", "50", "52", "54", "56", "58"],
    }

    # --- Materials ---
    MATERIALS = {
        "summer":      ["100% cotton", "Linen", "Viscose", "Silk", "Modal",
                        "Tencel", "Organic cotton", "Rayon", "Broderie anglaise"],
        "winter":      ["Merino wool", "Cashmere", "Mohair", "Fleece",
                        "Velvet", "Tweed", "Flannel", "Sherpa"],
        "denim":       ["100% cotton denim", "Stretch denim", "Organic denim",
                        "Recycled denim", "Washed cotton"],
        "sport":       ["Recycled polyester", "Nylon", "Spandex", "DryFit",
                        "Climalite", "Gore-Tex", "Thermolite", "Coolmax"],
        "accessories": ["Genuine leather", "Vegan leather", "Canvas",
                        "Nylon", "Raffia", "Woven straw"],
        "generic":     ["Cotton", "Polyester", "Elastane", "Acrylic",
                        "Bamboo", "Recycled cotton", "Sustainable materials"],
    }

    # --- Seasonal trends ---
    SEASONAL_TRENDS = {
        "spring_summer": {
            "keywords": ["floral", "pastel", "crochet", "embroidered",
                         "sheer", "co-ord", "pleated", "cutout"],
            "colors":   ["coral", "lavender", "lemon", "turquoise",
                         "powder pink", "sage green", "off-white"],
        },
        "autumn_winter": {
            "keywords": ["oversized", "teddy", "checked", "tartan",
                         "velvet", "leather", "knit", "layering"],
            "colors":   ["camel", "burgundy", "khaki", "chocolate",
                         "rust", "mustard", "forest green", "anthracite"],
        },
    }

    ADJECTIVES = [
        "Floral", "Oversized", "Slim fit", "Vintage", "Casual",
        "Elegant", "Striped", "Checked", "Embroidered", "Linen",
        "Denim", "Leather", "Knitted", "Printed", "Classic",
        "Bohemian", "Minimalist", "Romantic", "Sporty", "Chic",
        "Wrap", "Asymmetric", "Tailored", "Relaxed", "Cropped",
        "High-waisted", "Pleated", "Ruffled", "Sequined", "Velvet",
        "Satin", "Cotton", "Wool", "Silk", "Recycled", "Crochet",
        "Sheer", "Cut-out", "Ruched", "Smocked",
    ]

    PRODUCT_TYPES = {
        "women dresses":  ["Midi dress", "Mini dress", "Maxi dress", "Wrap dress",
                           "Shirt dress", "Slip dress", "Smock dress", "Bodycon dress",
                           "Crochet dress", "Cut-out dress", "Co-ord dress"],
        "women tops":     ["Blouse", "Crop top", "Tank top", "Shirt", "Bustier",
                           "Camisole", "Off-shoulder top", "Peplum top", "Corset top"],
        "women jeans":    ["Skinny jeans", "Mom jeans", "Wide leg jeans", "Straight jeans",
                           "Boyfriend jeans", "Flare jeans", "Cropped jeans", "Barrel jeans"],
        "women coats":    ["Trench coat", "Wool coat", "Puffer jacket", "Blazer",
                           "Teddy coat", "Denim jacket", "Leather jacket", "Raincoat"],
        "women sneakers": ["Running shoes", "Platform sneakers", "Low top sneakers",
                           "High top sneakers", "Chunky sneakers", "Slip-on sneakers"],
        "women bags":     ["Tote bag", "Shoulder bag", "Crossbody bag", "Mini bag",
                           "Clutch", "Backpack", "Bucket bag", "Saddle bag", "Raffia bag"],
        "women skirts":   ["Mini skirt", "Midi skirt", "Maxi skirt", "Pleated skirt",
                           "Wrap skirt", "Denim skirt", "Leather skirt", "Satin skirt"],
        "women blouses":  ["Silk blouse", "Printed blouse", "Ruffled blouse", "Linen blouse",
                           "Broderie blouse", "Wrap blouse"],
        "women knitwear": ["Crew neck sweater", "V-neck cardigan", "Turtleneck",
                           "Oversized knit", "Cable knit sweater", "Mohair sweater"],
        "women blazers":  ["Double breasted blazer", "Cropped blazer", "Oversized blazer",
                           "Check blazer", "Linen blazer", "Velvet blazer"],
        "women heels":    ["Stiletto heels", "Block heels", "Mules", "Wedge heels",
                           "Kitten heels", "Platform heels", "Slingback heels"],
        "women boots":    ["Ankle boots", "Knee-high boots", "Chelsea boots",
                           "Combat boots", "Over-the-knee boots", "Western boots"],
        "women sandals":  ["Flat sandals", "Heeled sandals", "Strappy sandals",
                           "Espadrilles", "Slides", "Mules"],
        "women jewelry":  ["Gold necklace", "Hoop earrings", "Stud earrings",
                           "Bracelet", "Ring set", "Pendant necklace", "Cuff bracelet"],
        "women shorts":   ["Denim shorts", "Linen shorts", "Tailored shorts",
                           "Cycling shorts", "High-waisted shorts", "Bermuda shorts"],
        "women trousers": ["Wide leg trousers", "Tailored trousers", "Linen trousers",
                           "Cargo trousers", "Cigarette trousers", "Palazzo trousers"],
        "men t-shirts":   ["Crew neck tee", "V-neck tee", "Polo shirt", "Graphic tee",
                           "Longline tee", "Oversized tee", "Henley shirt"],
        "men jeans":      ["Slim jeans", "Straight jeans", "Tapered jeans", "Relaxed jeans",
                           "Skinny jeans", "Wide leg jeans", "Distressed jeans"],
        "men sneakers":   ["Running shoes", "High top sneakers", "Low top sneakers",
                           "Chunky sneakers", "Slip-on sneakers", "Basketball shoes"],
        "men coats":      ["Trench coat", "Puffer jacket", "Wool coat", "Bomber jacket",
                           "Denim jacket", "Leather jacket", "Raincoat", "Peacoat"],
        "men shirts":     ["Oxford shirt", "Linen shirt", "Flannel shirt", "Denim shirt",
                           "Printed shirt", "Slim fit shirt", "Casual shirt",
                           "Camp collar shirt"],
        "men knitwear":   ["Crew neck sweater", "V-neck jumper", "Cardigan",
                           "Turtleneck", "Cable knit sweater", "Zip-up hoodie"],
        "men blazers":    ["Suit blazer", "Casual blazer", "Double breasted blazer",
                           "Linen blazer", "Check blazer", "Velvet blazer"],
        "men trousers":   ["Chinos", "Cargo trousers", "Tailored trousers",
                           "Linen trousers", "Joggers", "Track pants",
                           "Wide leg trousers"],
        "men boots":      ["Chelsea boots", "Combat boots", "Desert boots",
                           "Hiking boots", "Ankle boots", "Western boots"],
        "men bags":       ["Backpack", "Messenger bag", "Tote bag", "Gym bag", "Belt bag"],
        "men shorts":     ["Chino shorts", "Denim shorts", "Swim shorts",
                           "Sports shorts", "Cargo shorts", "Linen shorts"],
        "girls dresses":  ["Floral dress", "Denim dress", "Party dress",
                           "Tutu dress", "Smock dress", "Pinafore dress"],
        "girls tops":     ["Printed tee", "Ruffle top", "Crop top", "Tank top",
                           "Polo shirt"],
        "girls jeans":    ["Skinny jeans", "Straight jeans", "Flare jeans", "Mom jeans"],
        "girls coats":    ["Wool coat", "Puffer jacket", "Raincoat", "Denim jacket"],
        "girls sneakers": ["Canvas sneakers", "Platform sneakers", "Light-up sneakers"],
        "girls skirts":   ["Tutu skirt", "Denim skirt", "Pleated skirt", "Floral skirt"],
        "girls boots":    ["Chelsea boots", "Rain boots", "Ankle boots"],
        "boys t-shirts":  ["Graphic tee", "Polo shirt", "Sports tee",
                           "Striped tee", "Printed tee"],
        "boys shirts":    ["Oxford shirt", "Linen shirt", "Checked shirt"],
        "boys jeans":     ["Slim jeans", "Straight jeans", "Cargo jeans", "Relaxed jeans"],
        "boys coats":     ["Puffer jacket", "Raincoat", "Wool coat", "Bomber jacket"],
        "boys sneakers":  ["Running shoes", "High top sneakers", "Canvas sneakers"],
        "boys shorts":    ["Cargo shorts", "Sports shorts", "Denim shorts", "Swim shorts"],
    }

    COLORS = [
        "black", "white", "navy", "beige", "red", "green",
        "pink", "yellow", "grey", "brown", "blue", "orange",
        "camel", "ecru", "burgundy", "khaki", "coral", "lilac",
        "mint", "mustard", "rust", "sage", "teal", "ivory",
        "chocolate", "forest green", "powder pink", "stone",
        "off-white", "cobalt blue", "fuchsia", "electric blue",
    ]

    # --- Realistic product descriptions ---
    DESCRIPTION_TEMPLATES = [
        "{adjective} {product_type} in {material}. {fit} fit, perfect for {occasion}. "
        "Available in {color}. {trend_note}",
        "Discover this {adjective} {product_type} by {brand}. Made from {material}, "
        "it features a {fit} cut. Perfect for {occasion}.",
        "{brand} presents this trending {product_type} in {material}. "
        "Its {fit} cut suits all body types. {trend_note}",
    ]

    FITS = [
        "regular", "slim", "oversized", "relaxed", "straight",
        "fitted", "loose", "flared", "tapered", "wide",
    ]

    OCCASIONS = [
        "everyday wear", "the office", "going out", "evening events",
        "the weekend", "travelling", "special occasions",
        "casual days", "sport and fitness", "the beach",
    ]

    TREND_NOTES = [
        "Trend of the season.",
        "A wardrobe essential.",
        "Best-seller of the collection.",
        "Limited edition.",
        "Capsule piece of the season.",
        "New in the collection.",
        "Editor's pick.",
        "",  # Sometimes no trend note
    ]

    def __init__(self):
        # Skip the HTTP session — no network needed for mock data
        self.source_name = "mock"
        self._request_count = 0

    def _get_current_season(self) -> str:
        """Returns the current fashion season based on the current month."""
        month = datetime.now(timezone.utc).month
        if month in [3, 4, 5, 6, 7, 8]:
            return "spring_summer"
        return "autumn_winter"

    def _get_sizes(self, category: str) -> list[str]:
        """Returns realistic sizes based on the product category."""
        if category.startswith("girls"):
            pool = self.SIZES["girls"]
        elif category.startswith("boys"):
            pool = self.SIZES["boys"]
        elif any(x in category for x in ["sneakers", "boots", "heels", "sandals"]):
            pool = self.SIZES["women_shoes"] if "women" in category else self.SIZES["men_shoes"]
        elif "jeans" in category and "men" in category:
            pool = self.SIZES["men_jeans"]
        elif any(x in category for x in ["jewelry", "bags"]):
            pool = self.SIZES["one_size"]
        elif "men" in category:
            pool = self.SIZES["men"]
        else:
            pool = self.SIZES["women"]

        # Pick between 1 and all available sizes — never more than the pool size
        count = random.randint(1, len(pool))
        return sorted(random.sample(pool, k=count))

    def _get_material(self, category: str, season: str) -> str:
        """Returns a realistic material based on category and season."""
        if any(x in category for x in ["sneakers", "boots", "sport"]):
            return random.choice(self.MATERIALS["sport"])
        elif "jeans" in category:
            return random.choice(self.MATERIALS["denim"])
        elif any(x in category for x in ["bags", "jewelry"]):
            return random.choice(self.MATERIALS["accessories"])
        elif season == "spring_summer":
            return random.choice(self.MATERIALS["summer"])
        elif season == "autumn_winter":
            return random.choice(self.MATERIALS["winter"])
        else:
            return random.choice(self.MATERIALS["generic"])

    def _get_brand_and_price(self, category: str) -> tuple[str, float, bool, float | None]:
        """Returns a realistic brand and price based on category."""
        if category.startswith(("girls", "boys")):
            brand = random.choice(self.KIDS_BRANDS)
            price = round(random.uniform(8, 60), 2)

        elif any(x in category for x in ["sneakers", "boots"]):
            brand = random.choice(self.SPORT_BRANDS + self.STREETWEAR_BRANDS)
            price = round(random.uniform(40, 250), 2)

        elif "sport" in category:
            brand = random.choice(self.SPORT_BRANDS)
            price = round(random.uniform(30, 180), 2)

        else:
            segment = random.choices(
                ["luxury", "premium", "mid", "fast", "streetwear"],
                weights=[10, 20, 35, 25, 10],
            )[0]

            if segment == "luxury":
                brand = random.choice(self.LUXURY_BRANDS)
                price = round(random.uniform(150, 800), 2)
            elif segment == "premium":
                brand = random.choice(self.PREMIUM_BRANDS)
                price = round(random.uniform(60, 300), 2)
            elif segment == "mid":
                brand = random.choice(self.MID_BRANDS)
                price = round(random.uniform(20, 120), 2)
            elif segment == "streetwear":
                brand = random.choice(self.STREETWEAR_BRANDS)
                price = round(random.uniform(40, 300), 2)
            else:
                brand = random.choice(self.FAST_FASHION_BRANDS)
                price = round(random.uniform(5, 50), 2)

        # 30% chance of being on sale
        is_promo = random.random() < 0.3
        original_price = round(price * random.uniform(1.2, 1.6), 2) if is_promo else None

        return brand, price, is_promo, original_price

    def _build_description(
        self,
        adjective: str,
        product_type: str,
        brand: str,
        material: str,
        color: str,
        season: str,
    ) -> str:
        """Generates a realistic product description."""
        trend_note = random.choice(self.TREND_NOTES)
        template = random.choice(self.DESCRIPTION_TEMPLATES)

        return template.format(
            adjective=adjective.lower(),
            product_type=product_type.lower(),
            brand=brand,
            material=material.lower(),
            fit=random.choice(self.FITS),
            occasion=random.choice(self.OCCASIONS),
            color=color,
            trend_note=trend_note,
        ).strip()

    def scrape(self, max_products: int) -> Iterator[RawProduct]:
        """Generates random but realistic mock products."""
        season = self._get_current_season()

        for i in range(max_products):
            category = random.choice(self.CATEGORIES)
            brand, price, is_promo, original_price = self._get_brand_and_price(category)
            adjective = random.choice(self.ADJECTIVES)
            product_types = self.PRODUCT_TYPES.get(category, ["Item"])
            product_type = random.choice(product_types)
            material = self._get_material(category, season)
            sizes = self._get_sizes(category)
            colors = random.sample(self.COLORS, k=random.randint(1, 4))
            source = random.choice(self.SOURCES)
            product_id = random.randint(100000, 999999)

            description = self._build_description(
                adjective, product_type, brand,
                material, colors[0], season,
            )

            # Add seasonal trend keywords to extra
            trend_data = self.SEASONAL_TRENDS[season]
            trend_keywords = random.sample(
                trend_data["keywords"],
                k=random.randint(1, 3),
            )

            yield RawProduct(
                source=source,
                url=f"https://www.{source}.com/fr/product/{product_id}",
                title=f"{adjective} {product_type} {brand}",
                price_raw=str(price),
                currency="EUR",
                category_raw=category,
                brand=brand,
                image_url=f"https://cdn.{source}.com/images/{product_id}.jpg",
                colors=colors,
                sizes=sizes,
                scraped_at=datetime.now(timezone.utc),
                extra={
                    "has_promo": is_promo,
                    "promo_price": original_price,
                    "product_id": str(product_id),
                    "material": material,
                    "description": description,
                    "season": season,
                    "trend_keywords": trend_keywords,
                    "fit": random.choice(self.FITS),
                },
            )