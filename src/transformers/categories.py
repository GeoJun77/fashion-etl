# src/transformers/categories.py
# Maps raw category labels from every source to one normalized taxonomy : "<audience>_<type>"
#
# Raw labels look very different depending on the source :
#   Vinted        : "women dresses"
#   Sneakin       : "Lifestyle > Sneakers > Junior > Mixte"
#   Kastner&Öhler : "Hommes > Vêtements > Pantalons et shorts > Chinos"
# So instead of a fixed lookup table, we detect the audience and the product type
# with French + English keywords.

import re
import unicodedata

# Audience keywords — checked in this order (girls before women, boys before men...)
AUDIENCES = [
    ("girls",  r"filles?|girls?"),
    ("boys",   r"garcons?|boys?"),
    ("kids",   r"junior|enfants?|kids?|baby|bebes?"),
    ("women",  r"femmes?|women|woman|dames?"),
    ("men",    r"hommes?|men|man"),
    ("unisex", r"mixte|unisexe?"),
]

# Product type keywords — order matters inside a label :
# specific types first ("short de bain" is swimwear, not shorts ; "t-shirt" is a top, not a shirt)
PRODUCT_TYPES = [
    ("swimwear",    r"maillot|bikini|short de bain|swim"),
    ("underwear",   r"soutien|culotte|boxer|slip|string|tanga|collant|lingerie|sous-vetement|pyjama|nuisette|underwear|panties"),
    ("sportswear",  r"legging|jogging|survetement|brassiere|sportswear|tracksuit"),
    ("beauty",      r"parfum|beaute|cosmeti|fragrance"),
    ("bags",        r"sacs?\b|sac a|sacoche|pochette|cabas|bagage|valise|bags?\b|backpack"),
    ("jewelry",     r"bijou|collier|bracelet|bague|boucles? d.oreille|montre|jewel|watch"),
    ("accessories", r"ceinture|chapeau|casquette|bonnet|bob\b|beret|echarpe|foulard|gant|lunette|cravate|chaussette|portefeuille"
                    r"|accessoire|belts?\b|hats?\b|caps?\b|scar(?:f|ves)|sunglass|socks?\b|wallet"),
    ("heels",       r"escarpin|talon|heels?\b"),
    ("boots",       r"bottine|bottes?\b|boots?\b"),
    ("sandals",     r"sandale|tongs?\b|nu-pied|claquette|mules?\b|sandals?\b"),
    ("sneakers",    r"sneaker|basket|trainers?\b"),
    ("shoes",       r"chaussure|chausson|ballerine|mocassin|derb|sabot|espadrille|shoes?\b|flats?\b|loafer"),
    ("blazers",     r"blazer|costume|tailleur|suits?\b"),
    ("coats",       r"manteau|doudoune|parka|veste|blouson|bomber|impermeable|trench|anorak|coupe-vent|coats?\b|jackets?\b"),
    ("dresses",     r"robes?\b|combinaison|dress|jumpsuit"),
    ("skirts",      r"jupe|skirt"),
    ("jeans",       r"jean"),
    ("shorts",      r"short|bermuda"),
    ("trousers",    r"pantalon|chino|cargo|trousers?\b|pants?\b"),
    ("knitwear",    r"pull|cardigan|gilet|maille|knit|sweater"),
    ("sweatshirts", r"sweat|hoodie|polaire|fleece"),
    ("blouses",     r"chemisier|blouse|tunique"),
    ("tops",        r"t-?shirt|tee\b|debardeur|tops?\b|polo|hauts?\b|body|tank"),
    ("shirts",      r"chemise|surchemise|shirt"),
]

_AUDIENCE_RE = [(name, re.compile(rf"\b(?:{pattern})\b")) for name, pattern in AUDIENCES]
_TYPE_RE = [(name, re.compile(rf"\b(?:{pattern})")) for name, pattern in PRODUCT_TYPES]

# Types that do not depend on the audience
AUDIENCE_FREE = {"beauty"}

# Types that win wherever they appear in a hierarchical label
DOMINANT_TYPES = {"swimwear", "underwear", "beauty"}


def _normalize_text(text: str) -> str:
    """Lowercases and strips accents : "Débardeur" -> "debardeur"."""
    nfkd = unicodedata.normalize("NFKD", text.lower())
    return nfkd.encode("ascii", "ignore").decode("ascii")


def detect_audience(text: str) -> str:
    text = _normalize_text(text)
    for name, regex in _AUDIENCE_RE:
        if regex.search(text):
            return name
    return "unisex"


def detect_type(text: str) -> str | None:
    """
    Returns the product type found in a label, or None.
    Hierarchical labels ("A > B > C") are read from the most specific level up.
    """
    normalized = _normalize_text(text)

    # Some parent levels decide on their own : "Sous-vêtements > Chemises" is underwear
    for name, regex in _TYPE_RE:
        if name in DOMINANT_TYPES and regex.search(normalized):
            return name

    segments = [s for s in re.split(r">|/", normalized) if s.strip()]
    for segment in reversed(segments):
        for name, regex in _TYPE_RE:
            if regex.search(segment):
                # "Costumes > Vestes" is a suit jacket, not a coat
                if name == "coats" and "costume" in normalized:
                    return "blazers"
                return name
    return None


def normalize_category(category_raw: str, title: str = "") -> str:
    """
    Returns a normalized category such as "women_dresses" or "kids_sneakers".
    Falls back on the product title when the raw label has no product type.
    Returns "other" when nothing matches.
    """
    category_raw = category_raw or ""
    product_type = detect_type(category_raw) or detect_type(title or "")
    if product_type is None:
        return "other"
    if product_type in AUDIENCE_FREE:
        return product_type

    audience = detect_audience(category_raw)
    if audience == "unisex" and title:
        audience = detect_audience(title)
    return f"{audience}_{product_type}"
