import rss from '@astrojs/rss';
import { getCollection } from 'astro:content';

export async function GET(context) {
    const allEvents = (await getCollection('events'))
    const events = allEvents.filter((e) =>
        e.data.date >= new Date(Date.now()).toISOString().split("T")[0])
        .sort(
            (a, b) =>
                parseInt(a.data.date.replaceAll("-", "")) -
                parseInt(b.data.date.replaceAll("-", "")),
        );
    return rss({
        title: 'UKHC Events',
        description: 'Upcoming UKHC Events.',
        site: 'https://localhost:4321',
        items: events.map((event) => ({
            city: event.data.city,
            title: event.data.title,
            pubDate: event.data.pub_date,
            date: event.data.date,
            description: event.data.description,
            link: event.data.link,
        })),
        stylesheet: "/rss/style.xsl",
    });
}