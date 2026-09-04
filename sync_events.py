import json
from datetime import datetime
from pathlib import Path

EVENTS_FILE = "src/lib/events.json"
EXPORT_FILE = "formspree_export.json"

FIELD_MAP = {
    "city": "city",
    "title": "title",
    "date": "date",
    "venue": "venue",
    "description": "description",
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


def main():
    # load existing events
    if Path(EVENTS_FILE).exists():
        with open(EVENTS_FILE) as f:
            events = json.load(f)
    else:
        events = []

    existing_keys = {(e["title"].lower(), e["date"]) for e in events}
    max_id = max((e["id"] for e in events), default=-1)

    # load Formspree export
    with open(EXPORT_FILE) as f:
        export = json.load(f)

    submissions = export.get("submissions", [])
    new_events = []

    for sub in submissions:
        # build event from mapped fields
        event_data = {k: sub.get(v) for k, v in FIELD_MAP.items()}

        if not all([event_data["city"], event_data["title"], event_data["date"]]):
            print("Skipping incomplete submission")
            continue

        key = (event_data["title"].lower(), event_data["date"])
        if key in existing_keys:
            print(f"Skipping duplicate: {event_data['title']} on {event_data['date']}")
            continue

        pub_date = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0000")

        new_events.append({
            "id": 0,
            "city": event_data["city"],
            "title": event_data["title"],
            "date": event_data["date"],
            "venue": event_data.get("venue", ""),
            "description": event_data.get("description", ""),
            "link": event_data.get("link", ""),
            "image_url": generate_image_url(event_data["date"], event_data["title"]),
            "pub_date": pub_date,
        })
        existing_keys.add(key)
        max_id += 1

    # assign IDs
    for i, evt in enumerate(new_events):
        evt["id"] = max_id - len(new_events) + 1 + i

    # merge and sort by date
    events.extend(new_events)
    events.sort(key=lambda e: (e["date"], e["title"]))

    # write back
    with open(EVENTS_FILE, "w") as f:
        json.dump(events, f, indent=4, ensure_ascii=False)
        f.write("\n")

    print(f"Added {len(new_events)} event(s) to {EVENTS_FILE}")


if __name__ == "__main__":
    main()
