"""Source configuration for The Bosphorus Brief.

Each feed: id, source (display label), url, category, weight (0-3, editorial
priority when picking top stories), max (items to keep per fetch).

Categories: turkiye, region, migration, safety, economy.

Google News RSS query feeds are used as a resilient backbone (they aggregate
many outlets and rarely go down); direct outlet feeds add depth. Any feed can
fail without breaking the run.
"""

GOOGLE_NEWS = "https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"

# Specialist feeds with global scope are kept only when a story touches the
# region; matched case-insensitively against title + summary.
REGION_WORDS = [
    "turkey", "türkiye", "turkish", "syria", "iran", "iraq", "lebanon",
    "egypt", "israel", "jordan", "middle east", "central asia", "caucasus",
    "azerbaijan", "gulf",
]


def gn(query: str) -> str:
    from urllib.parse import quote
    return GOOGLE_NEWS.format(q=quote(query))


FEEDS = [
    # ------------------------------------------------------------- Türkiye --
    # hurriyetdailynews.com and dailysabah.com serve empty RSS, so both come
    # in through Google News site: queries instead — keeping the
    # pro-government side of the spectrum represented in the feed.
    {"id": "gn-hdn", "source": "Google News", "category": "turkiye",
     "weight": 2, "max": 10, "url": gn('site:hurriyetdailynews.com when:3d')},
    {"id": "turkishminute", "source": "Turkish Minute", "category": "turkiye",
     "weight": 2, "max": 12, "url": "https://www.turkishminute.com/feed/"},
    {"id": "gn-sabah", "source": "Google News", "category": "turkiye",
     "weight": 1, "max": 10, "url": gn('site:dailysabah.com when:2d')},
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
    # Sky's world feed is global; keep only stories touching the region.
    {"id": "sky-world", "source": "Sky News", "category": "region",
     "weight": 1, "max": 10,
     "url": "https://feeds.skynews.com/feeds/rss/world.xml",
     "require": REGION_WORDS},

    # ------------------------------------------- Migration & residency ----
    # infomigrants.net's RSS endpoint 404s; reach it through Google News.
    {"id": "gn-infomigrants", "source": "Google News", "category": "migration",
     "weight": 2, "max": 8, "url": gn('site:infomigrants.net when:14d'),
     "require": REGION_WORDS},
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

    # ------------------------------------------------- Rights & freedoms --
    # Legal security for foreign residents (deportations, entry bans,
    # residency refusals), court rulings including the ECtHR, and freedom
    # of belief and press across the region — read across mainstream,
    # official, and specialist rights monitors.
    {"id": "gn-rights-courts", "source": "Google News", "category": "rights",
     "weight": 3, "max": 10,
     "url": gn('Turkey ("European Court of Human Rights" OR ECtHR OR "Constitutional Court" OR lawsuit OR verdict) when:14d')},
    {"id": "gn-deportations", "source": "Google News", "category": "rights",
     "weight": 3, "max": 12,
     "url": gn('Turkey (deported OR deportation OR "entry ban" OR "N-82" OR "G-87" OR "tahdit kodu" OR "visa denial" OR "residence permit rejected") when:30d')},
    {"id": "gn-belief", "source": "Google News", "category": "rights",
     "weight": 3, "max": 12,
     "url": gn('(Turkey OR Türkiye) ("religious freedom" OR "freedom of belief" OR "religious minority" OR church OR Christians OR Alevi OR synagogue) when:14d')},
    {"id": "gn-persecution", "source": "Google News", "category": "rights",
     "weight": 3, "max": 10,
     "url": gn('("religious persecution" OR "Christian persecution" OR "persecuted Christians") ("Middle East" OR Turkey OR Iran OR Syria OR Egypt) when:14d')},
    # Civil liberties beyond belief — LGBT-related bans, event restrictions,
    # and court cases (e.g. the July 2026 cruise turned away from Kuşadası
    # and İstanbul) were invisible to every query above.
    {"id": "gn-lgbt", "source": "Google News", "category": "rights",
     "weight": 2, "max": 8,
     "url": gn('(Turkey OR Türkiye OR Istanbul) (LGBT OR LGBTI OR LGBTQ OR gay OR lesbian OR transgender OR "pride march") when:14d')},
    {"id": "forum18", "source": "Google News", "category": "rights",
     "weight": 2, "max": 6,
     "url": gn('site:forum18.org OR "Forum 18" when:30d'),
     "require": REGION_WORDS},
    {"id": "morningstar", "source": "Morning Star News", "category": "rights",
     "weight": 3, "max": 8, "url": "https://morningstarnews.org/feed/",
     "require": REGION_WORDS},
    # Google News backstop for the same outlet — the direct feed often has
    # no region items in the window.
    {"id": "gn-morningstar", "source": "Google News", "category": "rights",
     "weight": 3, "max": 6, "url": gn('site:morningstarnews.org when:30d'),
     "require": REGION_WORDS},
    {"id": "icc", "source": "International Christian Concern", "category": "rights",
     "weight": 2, "max": 8, "url": "https://www.persecution.org/feed/",
     "require": REGION_WORDS},
    # meconcern.org does not resolve from the build runner; go via Google News.
    {"id": "gn-meconcern", "source": "Google News", "category": "rights",
     "weight": 2, "max": 6,
     "url": gn('site:meconcern.org OR "Middle East Concern" when:30d')},

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
    "border", "airspace", "deport", "entry ban", "religious freedom",
    "freedom of belief", "echr", "rights court", "lgbt",
]

# ---------------------------------------------------------------------------
# Source lenses — ownership-based reading aids.
#
# Labels describe ownership and affiliation (matters of public record), not
# the quality of any article. For this region the meaningful spectrum is not
# left/right but state ↔ pro-government ↔ opposition ↔ independent ↔
# international. Sources not listed simply go unlabeled.

LENS_NOTES = {
    "state": "state-owned or state-funded outlet",
    "progov": "private outlet with pro-government ownership",
    "opposition": "opposition-leaning or exile-run outlet",
    "independent": "independent newsroom",
    "international": "international outlet or wire service",
    "official": "government or international body",
}

SOURCE_LENS = {
    # -- state-owned / state-funded ---------------------------------------
    "trt world": ("state", "Türkiye's public broadcaster"),
    "trt": ("state", "Türkiye's public broadcaster"),
    "trt haber": ("state", "Türkiye's public broadcaster"),
    "anadolu agency": ("state", "Türkiye's state news agency"),
    "anadolu ajansi": ("state", "Türkiye's state news agency"),
    "aa": ("state", "Türkiye's state news agency"),
    "al jazeera": ("state", "funded by the government of Qatar"),
    "aljazeera": ("state", "funded by the government of Qatar"),
    "al jazeera english": ("state", "funded by the government of Qatar"),
    "the new arab": ("state", "owned by Qatari media group Fadaat"),
    "new arab": ("state", "owned by Qatari media group Fadaat"),
    "al arabiya": ("state", "Saudi-owned broadcaster"),
    "arab news": ("state", "Saudi royal-linked SRMG media group"),
    "the national": ("state", "owned by an Abu Dhabi state-linked group"),
    "xinhua": ("state", "China's state news agency"),
    "cgtn": ("state", "China's state broadcaster"),
    "voice of america": ("state", "funded by the U.S. government"),
    "voa": ("state", "funded by the U.S. government"),
    "press tv": ("state", "Iran's state broadcaster"),
    "irna": ("state", "Iran's state news agency"),
    "tass": ("state", "Russia's state news agency"),
    "rt": ("state", "Russian state-funded broadcaster"),
    "sputnik": ("state", "Russian state-funded outlet"),
    "sana": ("state", "Syria's state news agency"),
    "wafa": ("state", "Palestinian Authority news agency"),
    "petra": ("state", "Jordan's state news agency"),
    "kuna": ("state", "Kuwait's state news agency"),
    "qna": ("state", "Qatar's state news agency"),
    "saudi press agency": ("state", None),
    "mena": ("state", "Egypt's state news agency"),

    # -- private, pro-government ownership (Türkiye) ----------------------
    "daily sabah": ("progov", "owned by the pro-government Turkuvaz group"),
    "sabah": ("progov", "owned by the pro-government Turkuvaz group"),
    "yeni safak": ("progov", "owned by the pro-government Albayrak group"),
    "hurriyet daily news": ("progov", "owned by the Demirören group"),
    "hurriyet": ("progov", "owned by the Demirören group"),
    "milliyet": ("progov", "owned by the Demirören group"),
    "cnn turk": ("progov", "owned by the Demirören group"),
    "demiroren news agency": ("progov", "owned by the Demirören group"),
    "dha": ("progov", "owned by the Demirören group"),
    "haberturk": ("progov", "owned by the Ciner group"),
    "ntv": ("progov", "owned by the Doğuş group"),
    "a news": ("progov", "owned by the pro-government Turkuvaz group"),
    "anews": ("progov", "owned by the pro-government Turkuvaz group"),
    "takvim": ("progov", "owned by the pro-government Turkuvaz group"),
    "aksam": ("progov", None),
    "star": ("progov", None),
    "turkiye today": ("progov", "part of the Albayrak media group"),
    "türkiye today": ("progov", "part of the Albayrak media group"),
    "ihlas news agency": ("progov", None),
    "iha": ("progov", None),
    "tgrt": ("progov", None),
    "yeni akit": ("progov", None),

    # -- opposition-leaning / exile-run -----------------------------------
    "turkish minute": ("opposition", "run by Turkish journalists in exile"),
    "nordic monitor": ("opposition", "run by Turkish journalists in exile"),
    "stockholm center for freedom": ("opposition", "run by Turkish journalists in exile"),
    "bold medya": ("opposition", None),
    "kronos": ("opposition", None),
    "tr724": ("opposition", None),
    "cumhuriyet": ("opposition", "Türkiye's oldest opposition daily"),
    "sozcu": ("opposition", "opposition-leaning daily"),
    "sözcü": ("opposition", "opposition-leaning daily"),
    "birgun": ("opposition", "left-leaning opposition daily"),
    "halk tv": ("opposition", "opposition-aligned broadcaster"),
    "tele1": ("opposition", "opposition-aligned broadcaster"),
    "duvar english": ("opposition", None),
    "gazete duvar": ("opposition", None),
    "medya news": ("opposition", "pro-Kurdish outlet"),
    "evrensel": ("opposition", "left-leaning daily"),

    # -- independent newsrooms --------------------------------------------
    "bianet": ("independent", "independent Turkish newsroom"),
    "t24": ("independent", "independent Turkish news site"),
    "medyascope": ("independent", "independent Turkish web broadcaster"),
    "diken": ("independent", None),
    "gazete oksijen": ("independent", None),
    "al-monitor": ("independent", "regional news site based in Washington"),
    "al monitor": ("independent", "regional news site based in Washington"),
    "middle east eye": ("independent", "independent; widely reported Qatari funding links"),
    "middle east monitor": ("independent", "pro-Palestinian advocacy outlet"),
    "bne intellinews": ("independent", "emerging-markets news service"),
    "turkey recap": ("independent", "independent newsletter by Türkiye-based journalists"),
    "yetkin report": ("independent", None),
    "times of israel": ("independent", "independent Israeli news site"),
    "haaretz": ("independent", "independent Israeli daily"),
    "jerusalem post": ("independent", "independent Israeli daily"),
    "ekathimerini": ("independent", "independent Greek daily"),
    "kathimerini": ("independent", "independent Greek daily"),
    "l'orient today": ("independent", "independent Lebanese daily"),
    "new lines magazine": ("independent", None),
    "syria direct": ("independent", None),
    "the syrian observer": ("independent", None),
    "enab baladi": ("independent", None),
    "rudaw": ("independent", "based in Iraqi Kurdistan, KDP-linked"),
    "levant24": ("independent", None),

    # -- international outlets & wires ------------------------------------
    "bbc": ("international", "publicly funded under UK royal charter"),
    "bbc news": ("international", "publicly funded under UK royal charter"),
    "reuters": ("international", "international wire service"),
    "associated press": ("international", "international wire service"),
    "ap": ("international", "international wire service"),
    "ap news": ("international", "international wire service"),
    "afp": ("international", "international wire service"),
    "agence france-presse": ("international", "international wire service"),
    "cnn": ("international", None),
    "bloomberg": ("international", None),
    "financial times": ("international", None),
    "the guardian": ("international", None),
    "guardian": ("international", None),
    "new york times": ("international", None),
    "the new york times": ("international", None),
    "washington post": ("international", None),
    "the washington post": ("international", None),
    "wall street journal": ("international", None),
    "the wall street journal": ("international", None),
    "the economist": ("international", None),
    "economist": ("international", None),
    "deutsche welle": ("international", "Germany's publicly funded international broadcaster"),
    "dw": ("international", "Germany's publicly funded international broadcaster"),
    "france 24": ("international", "France's publicly funded international broadcaster"),
    "euronews": ("international", None),
    "sky news": ("international", None),
    "npr": ("international", "U.S. public radio"),
    "abc news": ("international", None),
    "nbc news": ("international", None),
    "cbs news": ("international", None),
    "fox news": ("international", None),
    "politico": ("international", None),
    "axios": ("international", None),
    "newsweek": ("international", None),
    "time": ("international", None),
    "forbes": ("international", None),
    "business insider": ("international", None),
    "the independent": ("international", None),
    "independent": ("international", None),
    "the telegraph": ("international", None),
    "telegraph": ("international", None),
    "the times": ("international", None),
    "cnbc": ("international", None),
    "marketwatch": ("international", None),
    "trading economics": ("international", "market-data service"),
    "tradingpedia": ("international", "market-analysis site"),
    "fxstreet": ("international", "market-analysis site"),
    "investing.com": ("international", "market-data service"),
    "infomigrants": ("international", "publicly funded European consortium"),
    "google news": ("international", None),

    # -- rights & freedom-of-belief monitors -------------------------------
    "forum 18": ("independent", "religious-freedom news service covering all faiths"),
    "morning star news": ("independent", "newswire covering persecution of Christians worldwide"),
    "international christian concern": ("independent", "religious-liberty advocacy organization"),
    "middle east concern": ("independent", "religious-liberty advocacy group for the region"),
    "christianity today": ("independent", "US-based Christian magazine"),
    "christian daily international": ("independent", "religious-liberty news service"),
    "open doors": ("independent", "religious-liberty advocacy organization"),
    "world watch monitor": ("independent", "religious-liberty news service"),
    "premier christian news": ("independent", None),
    "catholic news agency": ("independent", None),
    "crux": ("independent", None),
    "article 18": ("independent", "documents freedom of religion or belief in Iran"),
    "human rights watch": ("independent", "international human-rights organization"),
    "amnesty international": ("independent", "international human-rights organization"),
    "committee to protect journalists": ("independent", "press-freedom organization"),
    "uscirf": ("official", "U.S. Commission on International Religious Freedom"),

    # -- wider financial & general press ----------------------------------
    "yahoo finance": ("international", None),
    "yahoo news": ("international", None),
    "msn": ("international", "syndication platform"),
    "fortune": ("international", None),
    "the hill": ("international", None),
    "foreign policy": ("international", None),
    "the atlantic": ("international", None),
    "semafor": ("international", None),
    "vox": ("international", None),
    "quartz": ("international", None),
    "barrons": ("international", None),
    "s&p global": ("international", "ratings and market intelligence"),
    "fitch ratings": ("international", "credit-rating agency"),
    "moodys": ("international", "credit-rating agency"),
    "seeking alpha": ("international", "investor commentary platform"),
    "benzinga": ("international", "market-news site"),
    "coindesk": ("international", "crypto-market news"),
    "cointelegraph": ("international", "crypto-market news"),
    "the conversation": ("international", "academic commentary network"),
    "daily mail": ("international", None),
    "the mirror": ("international", None),
    "the sun": ("international", None),
    "metro": ("international", None),
    "express": ("international", None),
    "evening standard": ("international", None),
    "inews": ("international", None),
    "greek reporter": ("independent", "Greek diaspora news site"),
    "balkan insight": ("independent", "investigative network BIRN"),
    "occrp": ("independent", "investigative journalism network"),
    "dunya": ("independent", "Turkish business daily"),
    "bloomberght": ("progov", "owned by the Doğuş group"),
    "turkiye gazetesi": ("progov", "part of the İhlas group"),

    # -- more regional outlets --------------------------------------------
    "gulf news": ("state", "UAE-aligned daily"),
    "khaleej times": ("state", "UAE-aligned daily"),
    "al mayadeen": ("state", "aligned with the Iran–Hezbollah axis"),
    "ahram online": ("state", "Egyptian state-owned"),
    "al ahram": ("state", "Egyptian state-owned"),
    "egypt today": ("state", "Egyptian pro-government"),
    "daily news egypt": ("independent", None),
    "jordan times": ("independent", "semi-official Jordanian daily"),
    "the jordan times": ("independent", "semi-official Jordanian daily"),
    "naharnet": ("independent", "Lebanese news site"),
    "kurdistan24": ("independent", "based in Iraqi Kurdistan, KDP-linked"),
    "shafaq news": ("independent", "Iraq-based news agency"),
    "amwaj media": ("independent", "covers Iran, Iraq and the Gulf"),
    "i24news": ("independent", "Israeli broadcaster"),
    "ynetnews": ("independent", "Israeli news site"),
    "ynet": ("independent", "Israeli news site"),

    # -- official sources --------------------------------------------------
    "u.s. state dept": ("official", "U.S. Department of State"),
    "us state department": ("official", "U.S. Department of State"),
    "uk fcdo": ("official", "UK Foreign, Commonwealth & Development Office"),
    "gov.uk": ("official", "UK government"),
    "reliefweb": ("official", "UN humanitarian information service"),
    "un news": ("official", "United Nations"),
    "unhcr": ("official", "UN refugee agency"),
    "iom": ("official", "UN migration agency"),
    "afad": ("official", "Türkiye's disaster management authority"),
}

# Sources that aren't news: broker chart pages, property listings, crypto
# promo blogs, metals tickers. Items from these are dropped outright.
SOURCE_BLOCKLIST = {
    "realtor", "zillow", "redfin", "forex", "tradingview", "bitget",
    "binance", "coinpedia", "watcher guru", "newsbtc", "coingape",
    "cryptopolitan", "ambcrypto", "shanghai metals market", "inshorts",
    "opera news", "xe", "wise", "exchange rates", "currency converter",
}

# Whole classes of source that only ever reach us through the word "turkey":
# poultry trade press, funeral notices, hunting magazines.
SOURCE_BLOCK_SUBSTRINGS = (
    "poultry", "funeral", "obituar", "memorial home", "meatingplace",
    "agweb", "drovers", "field & stream", "field and stream", "outdoor life",
)


def blocked_source(name: str) -> bool:
    key = _normalize_source(name)
    return key in SOURCE_BLOCKLIST or any(
        s in key for s in SOURCE_BLOCK_SUBSTRINGS)


# Prefix fallbacks, checked longest-first, for feed-name variants like
# "Reuters.com" or "BBC News Türkçe". Order matters: more specific first.
LENS_PREFIXES = [
    ("cnn turk", "progov"), ("al jazeera", "state"), ("trt", "state"),
    ("anadolu", "state"), ("hurriyet", "progov"), ("daily sabah", "progov"),
    ("yeni safak", "progov"), ("bbc", "international"),
    ("reuters", "international"), ("bloomberg", "international"),
    ("deutsche welle", "international"), ("middle east eye", "independent"),
    ("turkish minute", "opposition"), ("al-monitor", "independent"),
]

import unicodedata


def _normalize_source(name: str) -> str:
    text = unicodedata.normalize("NFKD", (name or "").lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.replace(".com", "").replace(".net", "").replace(".org", "")
    text = " ".join(t for t in text.replace("-", " ").split())
    return text


def source_lens(name: str):
    """Return {'code', 'note'} for a source display name, or None."""
    key = _normalize_source(name)
    if not key:
        return None
    hit = SOURCE_LENS.get(key) or SOURCE_LENS.get(key.removeprefix("the "))
    if hit:
        return {"code": hit[0], "note": hit[1] or LENS_NOTES[hit[0]]}
    for prefix, code in LENS_PREFIXES:
        if key.startswith(prefix):
            return {"code": code, "note": LENS_NOTES[code]}
    return None


# Recent seismic activity in and around Türkiye (Aegean to the Caucasus and
# northern Levant), M4.0+, newest first. USGS allows keyless, CORS-open
# access, so the client can also refresh this live.
QUAKES_URL = (
    "https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson"
    "&minmagnitude=4&orderby=time&limit=12"
    "&minlatitude=34&maxlatitude=43&minlongitude=24&maxlongitude=46"
)
