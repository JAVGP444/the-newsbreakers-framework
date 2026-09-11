import type { Article, GeoRow } from "./api";

/** Centroides ISO para que el mapa siempre tenga puntos aunque /geo venga vacío. */
export const COUNTRY_CENTROIDS: Record<string, { name: string; lat: number; lng: number }> = {
  MX: { name: "México", lat: 23.63, lng: -102.55 },
  US: { name: "Estados Unidos", lat: 39.83, lng: -98.58 },
  GT: { name: "Guatemala", lat: 15.78, lng: -90.23 },
  BZ: { name: "Belice", lat: 17.19, lng: -88.5 },
  HN: { name: "Honduras", lat: 15.2, lng: -86.24 },
  SV: { name: "El Salvador", lat: 13.79, lng: -88.9 },
  NI: { name: "Nicaragua", lat: 12.87, lng: -85.21 },
  CR: { name: "Costa Rica", lat: 9.75, lng: -83.75 },
  PA: { name: "Panamá", lat: 8.54, lng: -80.78 },
  CO: { name: "Colombia", lat: 4.57, lng: -74.3 },
  VE: { name: "Venezuela", lat: 6.42, lng: -66.59 },
  BR: { name: "Brasil", lat: -14.24, lng: -51.93 },
  AR: { name: "Argentina", lat: -38.42, lng: -63.62 },
  CL: { name: "Chile", lat: -35.68, lng: -71.54 },
  PE: { name: "Perú", lat: -9.19, lng: -75.02 },
  EC: { name: "Ecuador", lat: -1.83, lng: -78.18 },
  BO: { name: "Bolivia", lat: -16.29, lng: -63.59 },
  UY: { name: "Uruguay", lat: -32.52, lng: -55.77 },
  PY: { name: "Paraguay", lat: -23.44, lng: -58.44 },
  CU: { name: "Cuba", lat: 21.52, lng: -77.78 },
  DO: { name: "República Dominicana", lat: 18.74, lng: -70.16 },
  ES: { name: "España", lat: 40.46, lng: -3.75 },
  FR: { name: "Francia", lat: 46.23, lng: 2.21 },
  DE: { name: "Alemania", lat: 51.17, lng: 10.45 },
  GB: { name: "Reino Unido", lat: 55.38, lng: -3.44 },
  IT: { name: "Italia", lat: 41.87, lng: 12.57 },
  NL: { name: "Países Bajos", lat: 52.13, lng: 5.29 },
  CH: { name: "Suiza", lat: 46.82, lng: 8.23 },
  CN: { name: "China", lat: 35.86, lng: 104.2 },
  JP: { name: "Japón", lat: 36.2, lng: 138.25 },
  IN: { name: "India", lat: 20.59, lng: 78.96 },
  AU: { name: "Australia", lat: -25.27, lng: 133.78 },
  CA: { name: "Canadá", lat: 56.13, lng: -106.35 },
  ZA: { name: "Sudáfrica", lat: -30.56, lng: 22.94 },
  INT: { name: "Internacional", lat: 20, lng: -40 },
  XX: { name: "Sin ubicar", lat: 8, lng: -30 },
};

const ALIASES: [string, string][] = [
  ["mexico", "MX"],
  ["méxico", "MX"],
  ["estados unidos", "US"],
  ["united states", "US"],
  ["usa", "US"],
  ["colombia", "CO"],
  ["guatemala", "GT"],
  ["brasil", "BR"],
  ["brazil", "BR"],
  ["argentina", "AR"],
  ["españa", "ES"],
  ["spain", "ES"],
  ["china", "CN"],
  ["internacional", "INT"],
];

export function countryCode(raw: string | null | undefined): string {
  const t = (raw || "").trim();
  if (!t) return "XX";
  const up = t.toUpperCase();
  if (COUNTRY_CENTROIDS[up]) return up;
  const low = t.toLowerCase();
  for (const [alias, iso] of ALIASES) {
    if (low.includes(alias)) return iso;
  }
  return "XX";
}

export function hydratePoint(row: GeoRow): GeoRow {
  const code = countryCode(row.country || row.name);
  const meta = COUNTRY_CENTROIDS[code] || COUNTRY_CENTROIDS.XX;
  return {
    ...row,
    country: row.country || code,
    name: row.name || meta.name,
    lat: row.lat ?? meta.lat,
    lng: row.lng ?? meta.lng,
    count: row.count || row.articles?.length || 1,
    articles: row.articles || [],
  };
}

export function geoFromArticles(articles: Article[]): GeoRow[] {
  const buckets = new Map<string, GeoRow>();
  for (const a of articles) {
    const code = countryCode(a.country);
    const meta = COUNTRY_CENTROIDS[code] || COUNTRY_CENTROIDS.XX;
    const cur = buckets.get(code) || {
      country: code,
      name: meta.name,
      lat: meta.lat,
      lng: meta.lng,
      count: 0,
      articles: [],
    };
    cur.count += 1;
    if ((cur.articles?.length || 0) < 8) {
      cur.articles = [...(cur.articles || []), { content_id: a.content_id, title: a.title || a.url, risk_score: a.risk_score }];
    }
    buckets.set(code, cur);
  }
  return [...buckets.values()].sort((a, b) => b.count - a.count);
}

export function ensureGeoPoints(rows: GeoRow[], articles: Article[]): GeoRow[] {
  const hydrated = (rows || []).map(hydratePoint).filter((p) => p.lat != null && p.lng != null);
  if (hydrated.length) return hydrated;
  return geoFromArticles(articles);
}
