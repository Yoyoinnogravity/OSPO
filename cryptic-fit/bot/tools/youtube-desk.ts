import path from "node:path";
import { defineTool } from "@cursor/bdk/tools";
import { z } from "zod";
import { publishedSlugs, readText, siteRoot } from "../lib/site.js";

type UploadRow = {
  slug?: string;
  youtube_id?: string;
  uploaded_at?: string;
};

type UploadsFile = {
  channel?: string;
  videos?: UploadRow[];
  unmatched?: { youtube_id?: string; title?: string }[];
};

export default defineTool({
  description:
    "List cryptic.fit Shorts that are already on @crypticfit and those still pending. Reads the committed youtube-uploads.json. Does not upload anything.",
  effect: "read",
  inputSchema: z.object({}),
  async execute() {
    const root = siteRoot();
    const raw = await readText(path.join(root, "youtube-uploads.json"));
    let data: UploadsFile = {};
    if (raw) {
      try {
        data = JSON.parse(raw) as UploadsFile;
      } catch {
        data = {};
      }
    }
    const bySlug = new Map<string, UploadRow>();
    for (const row of data.videos ?? []) {
      if (row.slug) bySlug.set(row.slug, row);
    }
    const there: { slug: string; url: string; uploaded_at?: string }[] = [];
    const pending: string[] = [];
    for (const slug of await publishedSlugs(root)) {
      const id = bySlug.get(slug)?.youtube_id?.trim();
      if (id) {
        const row: { slug: string; url: string; uploaded_at?: string } = {
          slug,
          url: `https://www.youtube.com/shorts/${id}`,
        };
        const uploadedAt = bySlug.get(slug)?.uploaded_at;
        if (uploadedAt) row.uploaded_at = uploadedAt;
        there.push(row);
      } else {
        pending.push(slug);
      }
    }
    const undecided = (data.unmatched ?? [])
      .filter((row) => row.youtube_id)
      .map((row) => ({
        title: row.title ?? row.youtube_id,
        url: `https://www.youtube.com/shorts/${row.youtube_id}`,
      }));
    return {
      channel: data.channel ?? "@crypticfit",
      on_youtube: there,
      pending,
      undecided,
    };
  },
});
