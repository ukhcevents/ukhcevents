import hashlib
import json
import os
import re
import sqlite3
from dataclasses import dataclass, field
from typing import Optional

import feedparser
import requests
import requests as req
from bs4 import BeautifulSoup
from lxml import etree


def fetch_normal_rss(url: str) -> list[dict]:
    parsed = feedparser.parse(url)
    items = []
    for entry in parsed.entries:
        items.append({
            "id": getattr(entry, "id", None) or getattr(entry, "link", None),
            "title": getattr(entry, "title", None),
            "description": getattr(entry, "summary", None),
            "link": getattr(entry, "link", None),
            "published": getattr(entry, "published", None),
            "source_type": "normal_rss",
        })
    return items


def fetch_bigcartel_feed(url: str) -> list[dict]:
    resp = requests.get(url, timeout=30)
    tree = etree.fromstring(resp.content)

    ns = {"g": "http://base.google.com/ns/1.0"}

    items = []
    for item_elem in tree.findall(".//item"):

        def g(tag):
            elem = item_elem.find(f"g:{tag}", ns)
            return elem.text.strip() if elem is not None and elem.text else None

        items.append({
            "id": g("id"),
            "title": g("title"),
            "description": g("description"),
            "price": g("price"),
            "link": g("link"),
            "image_link": g("image_link"),
            "availability": g("availability"),
            "published": None,  # Big Cartel feeds don't include pubDate
            "source_type": "bigcartel",
        })
    return items


def scrape_to_items(url: str, selectors: dict) -> list[dict]:
    """
    Generic scraper driven by CSS selectors.
    `selectors` maps field names to CSS selectors.
    e.g. {"title": ".event-title", "date": ".event-date", "link": "a.event-link@href"}
    """
    resp = requests.get(url, timeout=30)
    soup = BeautifulSoup(resp.content, "html.parser")

    # Find the repeating container for each event/listing
    containers = soup.select(selectors["container"])

    items = []
    for c in containers:
        item = {}
        for field, selector in selectors.items():
            if field == "container":
                continue
            el = c.select_one(selector)
            if el:
                if "@href" in selector:
                    item[field] = el.get("href")
                else:
                    item[field] = el.get_text(strip=True)
        item["source_type"] = "scraped"
        items.append(item)
    return items


@dataclass
class FeedItem:
    id: str
    title: str
    description: str
    link: str
    published: Optional[str] = None
    source_url: str = ""
    source_type: str = ""
    raw: dict = field(default_factory=dict)  # original fields, kept for extraction


def init_db(db_path="seen_items.db"):
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS seen_items (
            item_hash TEXT PRIMARY KEY,
            source_url TEXT,
            title TEXT,
            first_seen TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    return conn


def item_hash(item: FeedItem) -> str:
    # Hash on id + title to catch renames too, or just id for dedup
    return hashlib.sha256(f"{item.source_url}:{item.id}".encode()).hexdigest()


def filter_new_items(conn, items: list[FeedItem]) -> list[FeedItem]:
    cur = conn.cursor()
    new_items = []
    for item in items:
        h = item_hash(item)
        cur.execute("SELECT 1 FROM seen_items WHERE item_hash = ?", (h,))
        if cur.fetchone() is None:
            new_items.append(item)
            cur.execute(
                "INSERT INTO seen_items (item_hash, source_url, title) VALUES (?, ?, ?)",
                (h, item.source_url, item.title),
            )
    conn.commit()
    return new_items


SHOW_KEYWORDS = [
    "gig",
    "live",
    "show",
    "concert",
    "tour",
    "tickets",
    "doors",
    "support",
    "venue",
    "admission",
    "all ages",
    "18+",
    "capacity",
    "sold out",
]


def likely_show(item: FeedItem) -> bool:
    text = f"{item.title} {item.description}".lower()
    return any(kw in text for kw in SHOW_KEYWORDS)


CLASSIFY_EXTRACT_PROMPT = """You are a gig listing extractor. Given the following feed item, determine:
1. Whether it is announcing a live music show/gig/concert (not a merchandise sale, blog post, etc.)
2. If yes, extract: city, title (band/event name), date (ISO format if possible), venue, link

Return JSON only:
{"is_show": true/false, "city": "", "title": "", "date": "", "venue": "", "link": ""}

Feed item title: {title}
Feed item description: {description}
Feed item link: {link}
"""


def classify_and_extract(item: FeedItem, api_key: str) -> dict | None:
    prompt = CLASSIFY_EXTRACT_PROMPT.format(
        title=item.title,
        description=item.description or "",
        link=item.link or "",
    )

    resp = req.post(
        "https://your-llm-api-endpoint/v1/chat/completions",  # LUMO ENDPOINT
        headers={"Authorization": f"Bearer {api_key}"},  # LUMO API KEY
        json={
            "model": "your-model",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
        },
        timeout=30,
    )
    content = resp.json()["choices"][0]["message"]["content"]
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return None


BIGCARTEL_TITLE_RE = re.compile(
    r"""
    .*?《           # opening bracket
    (?P<band>.+?)   # band/headliner name
    \s*@\s*         # @ separator
    (?P<venue>.+?)  # venue name
    \s+(\d{2})[•.](\d{2})[•.](\d{2,4})   # date like 16•09•26
    》              # closing bracket
    """,
    re.VERBOSE,
)


def extract_from_bigcartel_title(title: str) -> dict | None:
    m = BIGCARTEL_TITLE_RE.search(title)
    if not m:
        return None
    band, venue, day, month, year = m.groups()
    # Normalize year
    if len(year) == 2:
        year = f"20{year}"
    date_str = f"{year}-{month}-{day}"
    return {
        "is_show": True,
        "title": band.strip(),
        "venue": venue.strip(),
        "date": date_str,
        "city": "Manchester",  # Can extract from description address if needed
    }


def submit_to_formspree(extracted: dict, form_id: str) -> bool:
    resp = req.post(
        f"https://formspree.io/f/{form_id}",
        headers={"Content-Type": "application/json"},
        json={
            "city": extracted.get("city", ""),
            "title": extracted.get("title", ""),
            "date": extracted.get("date", ""),
            "venue": extracted.get("venue", ""),
            "link": extracted.get("link", ""),
        },
        timeout=15,
    )
    return resp.status_code in (200, 201)


def main():
    api_key = os.environ["LLM_API_KEY"]
    formspree_id = os.environ["FORMSPREE_ID"]
    conn = init_db()

    all_items = []

    # Category 1: Normal RSS
    for url in NORMAL_FEEDS:
        all_items.extend(fetch_normal_rss(url))

    # Category 2: Malformed/custom feeds (per-source adapters)
    for url in BIGCARTEL_FEEDS:
        all_items.extend(fetch_bigcartel_feed(url))
    # Add more adapters as needed...

    # Category 3: Scraped sites
    for site_config in SCRAPE_CONFIGS:
        items = scrape_to_items(site_config["url"], site_config["selectors"])
        all_items.extend(items)

    # Dedup
    new_items = filter_new_items(conn, all_items)
    print(f"Found {len(new_items)} new items")

    for item in new_items:
        if not likely_show(item):
            continue

        # Try structured extraction first (fast, free)
        extracted = None
        if item.source_type == "bigcartel":
            extracted = extract_from_bigcartel_title(item.title)
            if extracted:
                extracted["link"] = item.link

        # Fallback to LLM
        if extracted is None:
            extracted = classify_and_extract(item, api_key)

        if extracted and extracted.get("is_show"):
            success = submit_to_formspree(extracted, formspree_id)
            status = "submitted" if success else "submission failed"
            print(f"  [{status}] {extracted['title']} @ {extracted['venue']}")
