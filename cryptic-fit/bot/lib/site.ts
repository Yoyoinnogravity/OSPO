import { readdir, readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));

/** Published cryptic.fit site, next to this agent in the OSPO checkout. */
export function siteRoot(): string {
  return path.resolve(here, "../../../two-down/site");
}

export function londonDate(now = new Date()): string {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: "Europe/London",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(now);
}

export async function readText(file: string): Promise<string | null> {
  try {
    return await readFile(file, "utf8");
  } catch {
    return null;
  }
}

const CLUE = /<article\b[^>]*\bdata-slug="([^"]+)"[^>]*>([\s\S]*?)<\/article>/g;

export type ClueCard = {
  slug: string;
  kicker: string;
  clue: string;
};

/** Clue surfaces only. The answer paragraph is never copied out. */
export function clueCards(html: string): ClueCard[] {
  const cards: ClueCard[] = [];
  for (const match of html.matchAll(CLUE)) {
    const slug = match[1] ?? "";
    const body = match[2] ?? "";
    const kicker = body.match(/<p class="kicker">([^<]*)<\/p>/)?.[1]?.trim() ?? "";
    const clue = body.match(/<p class="clue-text">([^<]*)<\/p>/)?.[1]?.trim() ?? "";
    if (slug && clue) cards.push({ slug, kicker, clue });
  }
  return cards;
}

export async function publishedSlugs(root: string): Promise<string[]> {
  const clueRoot = path.join(root, "c");
  let names: string[] = [];
  try {
    names = await readdir(clueRoot);
  } catch {
    return [];
  }
  const slugs: string[] = [];
  for (const name of names.sort()) {
    const page = await readText(path.join(clueRoot, name, "index.html"));
    if (page !== null) slugs.push(name);
  }
  return slugs;
}
