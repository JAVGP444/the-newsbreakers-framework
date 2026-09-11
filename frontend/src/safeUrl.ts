const ALLOWED_SUFFIXES = [
  "woah.org",
  "oie.int",
  "fao.org",
  "who.int",
  "paho.org",
  "gob.mx",
  "cdc.gov",
  "usda.gov",
  "nih.gov",
  "un.org",
  "europa.eu",
  "youtube.com",
  "youtu.be",
  "openalex.org",
  "openstreetmap.org",
];

const BLOCKED = new Set([
  "example.invalid",
  "example.com",
  "example.org",
  "www.example.com",
  "www.example.org",
  "www.example.invalid",
  "social.local",
  "localhost",
  "127.0.0.1",
  "0.0.0.0",
]);

function hostOf(url: string): string {
  try {
    return new URL(url).hostname.toLowerCase().replace(/\.$/, "");
  } catch {
    return "";
  }
}

export function isAllowlistedHttp(url?: string | null): boolean {
  const raw = (url || "").trim();
  if (!raw) return false;
  let parsed: URL;
  try {
    parsed = new URL(raw);
  } catch {
    return false;
  }
  if (parsed.protocol !== "http:" && parsed.protocol !== "https:") return false;
  const host = parsed.hostname.toLowerCase().replace(/\.$/, "");
  if (!host || BLOCKED.has(host)) return false;
  if (host.endsWith(".example.com") || host.endsWith(".example.invalid")) return false;
  return ALLOWED_SUFFIXES.some((d) => host === d || host.endsWith(`.${d}`));
}

export function articleHref(contentId: string): string {
  return `/article/${encodeURIComponent(String(contentId || "").trim())}`;
}
