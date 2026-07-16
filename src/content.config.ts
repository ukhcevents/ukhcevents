import { defineCollection } from 'astro:content';
import { file } from 'astro/loaders';
import { z } from 'astro/zod';

const events = defineCollection({
    loader: file("src/lib/events.json"),
    schema: z.object({
        id: z.int(),
        city: z.string(),
        title: z.string(),
        date: z.string(),
        venue: z.string(),
        description: z.string(),
        link: z.string(),
        image_url: z.string(),
        pub_date: z.string()
    }),
});

export const collections = { events };