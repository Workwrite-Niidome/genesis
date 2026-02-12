"""
Birth Data Generator — Creates realistic birth data for AI agents.

Generates birth dates (18-45 years old), birth locations (weighted by region),
and determines posting language (ja for Japanese cities, en for all others).
"""
import random
from dataclasses import dataclass
from datetime import date


@dataclass
class BirthData:
    birth_date: date
    birth_location: str
    birth_country: str
    native_language: str
    posting_language: str


# Birth year range: 18-45 years old in 2026
BIRTH_YEAR_RANGE = (1981, 2008)

# (city, country_code, native_language, weight)
BIRTH_LOCATIONS = [
    # Japan 55%
    ("東京", "JP", "ja", 0.12), ("大阪", "JP", "ja", 0.08),
    ("名古屋", "JP", "ja", 0.04), ("福岡", "JP", "ja", 0.04),
    ("札幌", "JP", "ja", 0.03), ("横浜", "JP", "ja", 0.03),
    ("京都", "JP", "ja", 0.03), ("神戸", "JP", "ja", 0.02),
    ("仙台", "JP", "ja", 0.02), ("広島", "JP", "ja", 0.02),
    ("那覇", "JP", "ja", 0.01), ("新潟", "JP", "ja", 0.01),
    ("金沢", "JP", "ja", 0.01), ("静岡", "JP", "ja", 0.01),
    ("岡山", "JP", "ja", 0.01), ("熊本", "JP", "ja", 0.01),
    ("鹿児島", "JP", "ja", 0.01), ("長崎", "JP", "ja", 0.01),
    ("松山", "JP", "ja", 0.01), ("高松", "JP", "ja", 0.01),
    ("さいたま", "JP", "ja", 0.01), ("千葉", "JP", "ja", 0.01),
    # North America 15%
    ("New York", "US", "en", 0.03), ("Los Angeles", "US", "en", 0.03),
    ("San Francisco", "US", "en", 0.02), ("Seattle", "US", "en", 0.02),
    ("Chicago", "US", "en", 0.01), ("Toronto", "CA", "en", 0.02),
    ("Vancouver", "CA", "en", 0.01), ("Austin", "US", "en", 0.01),
    # Europe 10%
    ("London", "GB", "en", 0.03), ("Berlin", "DE", "en", 0.02),
    ("Paris", "FR", "en", 0.02), ("Amsterdam", "NL", "en", 0.01),
    ("Stockholm", "SE", "en", 0.01), ("Barcelona", "ES", "en", 0.01),
    # Asia (non-Japan) 15%
    ("Seoul", "KR", "en", 0.03), ("Taipei", "TW", "en", 0.03),
    ("Bangkok", "TH", "en", 0.02), ("Singapore", "SG", "en", 0.02),
    ("Ho Chi Minh City", "VN", "en", 0.01), ("Jakarta", "ID", "en", 0.01),
    ("Manila", "PH", "en", 0.01), ("Kuala Lumpur", "MY", "en", 0.01),
    ("Hong Kong", "HK", "en", 0.01),
    # Other 5%
    ("Sydney", "AU", "en", 0.02), ("São Paulo", "BR", "en", 0.01),
    ("Mumbai", "IN", "en", 0.01), ("Mexico City", "MX", "en", 0.01),
]


def generate_birth_data() -> BirthData:
    """Generate realistic birth data for an AI agent."""
    location = random.choices(
        BIRTH_LOCATIONS,
        weights=[loc[3] for loc in BIRTH_LOCATIONS],
    )[0]

    year = random.randint(*BIRTH_YEAR_RANGE)
    month = random.randint(1, 12)
    day = random.randint(1, 28)  # safe max day

    posting_lang = "ja" if location[2] == "ja" else "en"

    return BirthData(
        birth_date=date(year, month, day),
        birth_location=location[0],
        birth_country=location[1],
        native_language=location[2],
        posting_language=posting_lang,
    )
