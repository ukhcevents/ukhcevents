import json
from datetime import datetime
from io import BytesIO
from pathlib import Path

import requests
from PIL import Image

EVENTS_FILE = "src/lib/events.json"
ASSETS_DIR = Path("src/assets")
EXPORT_FILE = "formspree_export.json"

FIELD_MAP = {
    "city": "city",
    "title": "title",
    "date": "date",
    "venue": "venue",
    "link": "link",
}


def generate_image_url(date_str, title):
    clean_title = "".join(
        c if c.isalnum() or c in (" ", "-") else "-" for c in title.lower()
    )
    clean_title = "-".join(clean_title.split())
    while "--" in clean_title:
        clean_title = clean_title.replace("--", "-")
    clean_title = clean_title.strip("-")
    return f"/src/assets/{date_str}-{clean_title}.webp"


def download_event_image(image_field, date_str, title):
    # formspree returns list of urls, take the first
    url = image_field[0] if isinstance(image_field, list) else image_field
    if not url:
        return False

    resp = requests.get(url, timeout=30)
    resp.raise_for_status()

    image_url = generate_image_url(date_str, title)
    dest = ASSETS_DIR / Path(image_url.lstrip("/")).name

    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    img = Image.open(BytesIO(resp.content))
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    img.save(dest, "WEBP", quality=85)
    print(f"Saved image: {dest}")
    return True


def main():
    if Path(EVENTS_FILE).exists():
        with open(EVENTS_FILE) as f:
            events = json.load(f)
    else:
        events = []

    existing_keys = {(e["title"].lower(), e["date"]) for e in events}
    max_id = max((e["id"] for e in events), default=-1)

    with open(EXPORT_FILE) as f:
        export = json.load(f)

    new_events = []

    for sub in export.get("submissions", []):
        event_data = {k: sub.get(v) for k, v in FIELD_MAP.items()}

        if not all([event_data["city"], event_data["title"], event_data["date"]]):
            print("Skipping incomplete submission")
            continue

        key = (event_data["title"].lower(), event_data["date"])
        if key in existing_keys:
            print(f"Skipping duplicate: {event_data['title']} on {event_data['date']}")
            continue

        try:
            ok = download_event_image(
                sub.get("image"), event_data["date"], event_data["title"]
            )
        except Exception as e:
            print(f"Image download failed for {event_data['title']}: {e}")
            ok = False

        if not ok:
            print(f"Skipping {event_data['title']} (no usable image)")
            continue

        pub_date = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0000")

        description = input(
            f"Enter description for {event_data['title']} on {event_data['date']} "
            f"in {event_data['city']}: "
        )

        new_events.append({
            "id": 0,
            "city": event_data["city"],
            "title": event_data["title"],
            "date": event_data["date"],
            "venue": event_data.get("venue", ""),
            "description": description,
            "link": event_data.get("link", ""),
            "image_url": generate_image_url(event_data["date"], event_data["title"]),
            "pub_date": pub_date,
        })
        existing_keys.add(key)
        max_id += 1

    for i, evt in enumerate(new_events):
        evt["id"] = max_id - len(new_events) + 1 + i

    events.extend(new_events)
    events.sort(key=lambda e: (e["date"], e["title"]))

    with open(EVENTS_FILE, "w") as f:
        json.dump(events, f, indent=4, ensure_ascii=False)
        f.write("\n")

    print(f"Added {len(new_events)} event(s) to {EVENTS_FILE}")


if __name__ == "__main__":
    main()
