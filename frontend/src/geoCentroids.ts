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

/** Estados y condados que el mapa debe separar del centroide nacional. */
export const PLACE_CENTROIDS: Record<string, { name: string; country: string; lat: number; lng: number }> = {
  "US-TX-PRESIDIO": { name: "Presidio, Texas", country: "US", lat: 29.561, lng: -104.373 },
  "US-TX-JEFFDAVIS": { name: "Jeff Davis, Texas", country: "US", lat: 30.746, lng: -104.14 },
  "US-TX": { name: "Texas", country: "US", lat: 31.0, lng: -99.9 },
  "US-NM": { name: "Nuevo México", country: "US", lat: 34.41, lng: -106.11 },
  "US-AZ": { name: "Arizona", country: "US", lat: 34.27, lng: -111.66 },
  "US-CA": { name: "California", country: "US", lat: 36.78, lng: -119.42 },
  "US-FL": { name: "Florida", country: "US", lat: 27.66, lng: -81.52 },
  "US-IA": { name: "Iowa", country: "US", lat: 42.0, lng: -93.5 },
  "US-NC": { name: "Carolina del Norte", country: "US", lat: 35.76, lng: -79.02 },
  "MX-BC": { name: "Baja California", country: "MX", lat: 30.84, lng: -115.28 },
  "MX-CHIS": { name: "Chiapas", country: "MX", lat: 16.75, lng: -93.13 },
  "MX-OAX": { name: "Oaxaca", country: "MX", lat: 17.07, lng: -96.72 },
  "MX-TAB": { name: "Tabasco", country: "MX", lat: 17.84, lng: -92.62 },
  "MX-VER": { name: "Veracruz", country: "MX", lat: 19.17, lng: -96.13 },
  "MX-YUC": { name: "Yucatán", country: "MX", lat: 20.71, lng: -89.09 },
  "MX-CAM": { name: "Campeche", country: "MX", lat: 19.83, lng: -90.53 },
  "MX-ROO": { name: "Quintana Roo", country: "MX", lat: 19.18, lng: -88.05 },
  "MX-TAMPS": { name: "Tamaulipas", country: "MX", lat: 24.27, lng: -98.84 },
  "MX-NL": { name: "Nuevo León", country: "MX", lat: 25.59, lng: -99.99 },
  "MX-COAH": { name: "Coahuila", country: "MX", lat: 27.06, lng: -101.71 },
  "MX-CHIH": { name: "Chihuahua", country: "MX", lat: 28.63, lng: -106.07 },
  "MX-GTO": { name: "Guanajuato", country: "MX", lat: 21.02, lng: -101.26 },
  "MX-JAL": { name: "Jalisco", country: "MX", lat: 20.66, lng: -103.35 },
  "MX-SON": { name: "Sonora", country: "MX", lat: 29.3, lng: -110.93 },
  "MX-SIN": { name: "Sinaloa", country: "MX", lat: 25.17, lng: -107.48 },
  "MX-GRO": { name: "Guerrero", country: "MX", lat: 17.44, lng: -99.55 },
  "MX-PUE": { name: "Puebla", country: "MX", lat: 19.04, lng: -98.21 },
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
  if (up === "XX" || up === "INT") return up;
  if (COUNTRY_CENTROIDS[up]) return up;
  const low = t.toLowerCase();
  for (const [alias, iso] of ALIASES) {
    if (low === alias || low.includes(alias)) return iso;
  }
  return "XX";
}

export function pointKey(row: GeoRow): string {
  return (row.place_id || row.country || row.name || "").toUpperCase();
}

export function hydratePoint(row: GeoRow): GeoRow {
  if (row.unlocated) {
    return { ...row, unlocated: true, lat: undefined, lng: undefined };
  }
  const placeId = (row.place_id || "").toUpperCase();
  const place = PLACE_CENTROIDS[placeId];
  if (place) {
    return {
      ...row,
      place_id: placeId,
      country: row.country || place.country,
      name: row.name || place.name,
      lat: row.lat ?? place.lat,
      lng: row.lng ?? place.lng,
      grain: row.grain || "place",
      count: row.count || row.articles?.length || 1,
      articles: row.articles || [],
      unlocated: false,
    };
  }
  if (row.lat != null && row.lng != null && row.name) {
    return {
      ...row,
      count: row.count || row.articles?.length || 1,
      articles: row.articles || [],
      unlocated: false,
    };
  }
  const code = countryCode(row.country || row.name);
  const meta = COUNTRY_CENTROIDS[code];
  if (!meta || code === "XX" || code === "INT") {
    return { ...row, country: code || "XX", unlocated: true, lat: undefined, lng: undefined };
  }
  return {
    ...row,
    country: code,
    place_id: row.place_id || code,
    name: row.name && row.name !== row.country ? row.name : meta.name,
    lat: meta.lat,
    lng: meta.lng,
    grain: row.grain || "country",
    count: row.count || row.articles?.length || 1,
    articles: row.articles || [],
    unlocated: false,
  };
}

export function plottablePoints(rows: GeoRow[]): GeoRow[] {
  const buckets = new Map<string, GeoRow>();
  for (const row of rows || []) {
    const p = hydratePoint(row);
    if (p.unlocated || p.lat == null || p.lng == null) continue;
    const key = pointKey(p);
    const cur = buckets.get(key);
    if (!cur) {
      buckets.set(key, p);
      continue;
    }
    cur.count = (cur.count || 0) + (p.count || 0);
    const seen = new Set((cur.articles || []).map((a) => a.content_id));
    for (const a of p.articles || []) {
      if (seen.has(a.content_id) || (cur.articles || []).length >= 8) continue;
      cur.articles = [...(cur.articles || []), a];
    }
  }
  return [...buckets.values()].sort((a, b) => (b.count || 0) - (a.count || 0));
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
  const fromApi = plottablePoints(rows || []);
  if (fromApi.length) return fromApi;
  return plottablePoints(geoFromArticles(articles));
}
