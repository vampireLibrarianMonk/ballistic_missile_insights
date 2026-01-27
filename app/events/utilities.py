import geonamescache
import pycountry
import re

_gc = geonamescache.GeonamesCache()
_CITIES = _gc.get_cities()

def extract_country(text: str) -> str | None:
    text = text.lower()

    for country in pycountry.countries:
        # 1. Common name (highest signal)
        if hasattr(country, "common_name"):
            common = country.common_name.lower()
            if re.search(rf"\b{common}\b", text):
                return country.common_name

        # 2. Short-form derived name (e.g. "Russia" from "Russian Federation")
        short_name = country.name.split(",")[0].lower()

        # 2a. Derived noun form (Russian -> Russia)
        if short_name.endswith(" federation"):
            base = short_name.replace(" federation", "")
            if base.endswith("ian"):
                noun = base[:-3] + "ia"  # russian -> russia
                if re.search(rf"\b{noun}\b", text):
                    return noun.title()

        # 2b. Full short name fallback
        if re.search(rf"\b{short_name}\b", text):
            return short_name.title()

        # 3. Full standard name
        name = country.name.lower()
        if re.search(rf"\b{name}\b", text):
            return country.name

        # 4. Official long-form name
        if hasattr(country, "official_name"):
            official = country.official_name.lower()
            if re.search(rf"\b{official}\b", text):
                return country.name

    return None


def extract_city(text: str) -> str | None:
    """
    Extract a city name from text using GeoNames.
    Returns first high-confidence city match or None.
    """
    text = text.lower()

    for city in _CITIES.values():
        name = city["name"].lower()

        # Require word boundaries to avoid false positives
        if re.search(rf"\b{name}\b", text):
            return city["name"]

    return None
