import rss from '@astrojs/rss';
import { getCollection } from 'astro:content';

export async function getStaticPaths() {
    const allEvents = await getCollection("events");
    const cities = [...new Set(allEvents.map((e) => e.data.city))].sort();

    return cities.map((city) => {
        const events = allEvents.filter((e) => e.data.city === city
            && e.data.date >= new Date(Date.now()).toISOString().split("T")[0]);
        return {
            params: { city: city.toLowerCase() },
            props: { cityName: city, events },
        };
    });
}

export async function GET(context) {
    const cityParam = context.params.city;

    const allEvents = await getCollection('events');
    const events = allEvents.filter((e) =>
        e.data.city.toLowerCase() === cityParam
        && e.data.date >= new Date(Date.now()).toISOString().split("T")[0]
    ).sort(
        (a, b) =>
            parseInt(a.data.date.replaceAll("-", "")) -
            parseInt(b.data.date.replaceAll("-", "")),
    );

    const capitalizeCity = cityParam.charAt(0).toUpperCase() + cityParam.slice(1);

    return rss({
        title: `${capitalizeCity} - UKHC Events`,
        description: `Upcoming UKHC Events in ${capitalizeCity}.`,
        site: context.site || 'http://localhost:4321',
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