import json
import sqlite3

# export all the events from the db
with sqlite3.Connection("main.db") as conn:
    c = conn.cursor()
    c.execute("SELECT * FROM events")
    events = c.fetchall()

export = []
starting_id = 39
for event in events:
    event_json = {
        "id": starting_id,
        "city": event[1],
        "title": event[2],
        "date": event[3],
        "venue": event[5],
        "description": event[4],
        "link": event[6],
        "image_url": event[7],
        "pub_date": event[8]
    }
    export.append(event_json)
    starting_id += 1

# create a json using those dicts
with open("events.json", "w") as f:
    json.dump(export, f)