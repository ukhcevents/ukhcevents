# To Do

- Write the script for exporting events from formspree - ideally, wherever is hosting the site (via cloudflare pages?) will:
    1. Pull the submissions down from Formspree using the export API (this might have to be manual if it's behind the more expensive plan)
    2. I need to accept, edit or reject each submission. Ideally I could do this remotely but for now it can be done locally (or via SSH).
    3. The accepted events are added into the content collection JSON, and the site is rebuilt.

- Images - should be eagerly loaded for those which appear, and lazily loaded for those under the fold.

- City and Venue should automatically suggest based on any existing cities/venues.

- Set up Umami

- Deploy to Cloudflare Pages

- Make sure the site is rebuilt and redployed every day