"""Source configuration for The Bosphorus Brief.

Each feed: id, source (display label), url, category, weight (0-3, editorial
priority when picking top stories), max (items to keep per fetch).

Categories: turkiye, region, migration, safety, economy.

Google News RSS query feeds are used as a resilient backbone (they aggregate
many outlets and rarely go down); direct outlet feeds add depth. Any feed can
fail without breaking the run.
"""

GOOGLE_NEWS = "https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"


def gn(query: str) -> str:
    from urllib.parse import quote
    return GOOGLE_NEWS.format(q=quote(query))


FEEDS = [
    # ------------------------------------------------------------- Türkiye --
    {"id": "hdn", "source": "Hürriyet Daily News", "category": "turkiye",
     "weight": 2, "max": 12, "url": "https://www.hurriyetdailynews.com/rss"},
    {"id": "turkishminute", "source": "Turkish Minute", "category": "turkiye",
     "weight": 2, "max": 12, "url": "https://www.turkishminute.com/feed/"},
    {"id": "dailysabah", "source": "Daily Sabah", "category": "turkiye",
     "weight": 1, "max": 10, "url": "https://www.dailysabah.com/rss"},
    {"id": "gn-turkiye", "source": "Google News", "category": "turkiye",
     "weight": 2, "max": 15, "url": gn('Türkiye OR Turkey when:2d')},

    # ------------------------------------------------------- Wider region --
    {"id": "bbc-me", "source": "BBC", "category": "region",
     "weight": 3, "max": 15, "url": "https://feeds.bbci.co.uk/news/world/middle_east/rss.xml"},
    {"id": "aj", "source": "Al Jazeera", "category": "region",
     "weight": 2, "max": 15, "url": "https://www.aljazeera.com/xml/rss/all.xml"},
    {"id": "newarab", "source": "The New Arab", "category": "region",
     "weight": 1, "max": 10, "url": "https://www.newarab.com/rss"},
    {"id": "mee", "source": "Middle East Eye", "category": "region",
     "weight": 1, "max": 10, "url": "https://www.middleeasteye.net/rss"},

    # ------------------------------------------- Migration & residency ----
    {"id": "infomigrants", "source": "InfoMigrants", "category": "migration",
     "weight": 2, "max": 10, "url": "https://www.infomigrants.net/en/rss"},
    {"id": "gn-residency", "source": "Google News", "category": "migration",
     "weight": 3, "max": 12,
     "url": gn('Turkey ("residence permit" OR ikamet OR visa OR "work permit" OR citizenship OR deportation) when:14d')},
    {"id": "gn-refugees", "source": "Google News", "category": "migration",
     "weight": 2, "max": 10,
     "url": gn('Turkey (refugees OR "temporary protection" OR Syrians OR migration) when:7d')},
    {"id": "reliefweb-tur", "source": "ReliefWeb", "category": "migration",
     "weight": 1, "max": 8,
     "url": "https://reliefweb.int/updates/rss.xml?search=primary_country.iso3%3A%22tur%22"},

    # ------------------------------------------------------------ Safety --
    {"id": "gn-safety", "source": "Google News", "category": "safety",
     "weight": 2, "max": 12,
     "url": gn('Turkey (earthquake OR AFAD OR explosion OR "security alert" OR evacuation OR wildfire) when:3d')},
    {"id": "fcdo-turkey", "source": "UK FCDO", "category": "safety",
     "weight": 2, "max": 5, "url": "https://www.gov.uk/foreign-travel-advice/turkey.atom"},
    {"id": "gn-region-safety", "source": "Google News", "category": "safety",
     "weight": 1, "max": 10,
     "url": gn('(Syria OR Iraq OR Iran OR Lebanon) (strike OR attack OR ceasefire OR border) when:2d')},

    # ----------------------------------------------------------- Economy --
    {"id": "gn-lira", "source": "Google News", "category": "economy",
     "weight": 3, "max": 12,
     "url": gn('"Turkish lira" OR "Turkey inflation" OR "Turkey central bank" OR "Turkey economy" when:7d')},
    {"id": "gn-cost", "source": "Google News", "category": "economy",
     "weight": 1, "max": 8,
     "url": gn('Turkey (rent OR "minimum wage" OR prices OR "interest rate") when:7d')},
]

# U.S. State Department travel advisories (all countries, one feed).
ADVISORY_FEED = "https://travel.state.gov/_res/rss/TAsTWs.xml"

# Countries shown in the advisory panel, in display order.
ADVISORY_COUNTRIES = [
    "Turkey", "Türkiye", "Syria", "Iraq", "Iran", "Lebanon", "Israel",
    "Jordan", "Egypt", "Cyprus", "Greece", "Georgia", "Armenia", "Azerbaijan",
]

# Display-name fixups (feed title -> panel label).
ADVISORY_LABELS = {"Turkey": "Türkiye", "Türkiye": "Türkiye"}

# Exchange rates: free, keyless. Base USD; TRY crosses computed from it.
RATES_URL = "https://open.er-api.com/v6/latest/USD"
RATE_PAIRS = ["USD/TRY", "EUR/TRY", "GBP/TRY"]

# Words that nudge a story into the Top Stories mix.
BOOST_WORDS = [
    "türkiye", "turkey", "istanbul", "ankara", "izmir", "lira", "erdoğan",
    "erdogan", "earthquake", "residence permit", "ikamet", "visa", "refugee",
    "syria", "iran", "ceasefire", "inflation", "central bank", "airport",
    "border", "airspace",
]
