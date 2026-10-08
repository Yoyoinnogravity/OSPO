import path from "node:path";
import { defineTool } from "@cursor/bdk/tools";
import { z } from "zod";
import { clueCards, londonDate, readText, siteRoot } from "../lib/site.js";

export default defineTool({
  description:
    "Read today's cryptic.fit pair for the London date. Returns the two clue surfaces if the day page exists. Never returns an answer.",
  effect: "read",
  inputSchema: z.object({
    date: z
      .string()
      .regex(/^\d{4}-\d{2}-\d{2}$/)
      .optional()
      .describe("London calendar date YYYY-MM-DD. Defaults to today in Europe/London."),
  }),
  async execute({ date }) {
    const day = date ?? londonDate();
    const root = siteRoot();
    const page = path.join(root, "d", day, "index.html");
    const html = await readText(page);
    if (html === null) {
      return {
        date: day,
        published: false,
        clues: [],
        note: "No pair on the site for this London date. Do not invent clues.",
      };
    }
    return {
      date: day,
      published: true,
      path: `two-down/site/d/${day}/index.html`,
      clues: clueCards(html),
    };
  },
});
