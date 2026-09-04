# To Do

- Set up an RSS Reader which
    1. Pulls in from a bunch of feeds, and which also corrects feeds (e.g. bigcartel feeds) as well as creates feeds for sites that don't have them.
    2. Refreshes the feeds (ideally live as some kind of daemon) and when new items are added, they should be categorised based on whether they contain a show announcment.
        - If they do, then the JSON object for that show should be generated, and the form submitted via Formspree - using curl?

- Write the script for exporting events from formspree - ideally, wherever is hosting the site (via cloudflare pages?) will:
    1. Pull the submissions down from Formspree using the export API (this might have to be manual if it's behind the more expensive plan)
    2. I need to accept, edit or reject each submission. Ideally I could do this remotely but for now it can be done locally (or via SSH).
    3. The accepted events are added into the content collection JSON, and the site is rebuilt.

- Images - should be eagerly loaded for those which appear, and lazily loaded for those under the fold.

- City and Venue should automatically suggest based on any existing cities/venues.

```
city	"Birmingham"
title	"pilljun"
date	"2026-08-02"
venue	"uhibhiu"
source	"link"
ticket_link	"https://ukhc.events"
link	"https://ukhc.events"
```
```
city	"Birmingham"
title	"pilljun"
date	"2026-08-02"
venue	"uhibhiu"
source	"free"
link	"Free"
```
```
city	"Birmingham"
title	"pilljun"
date	"2026-08-02"
venue	"uhibhiu"
source	"doors"
link	"Doors"
```