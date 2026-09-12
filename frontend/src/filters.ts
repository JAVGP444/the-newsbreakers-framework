export type ObservatoryFilters = {
  disease: string | null;
  compare: string[];
  from: string | null;
  to: string | null;
  country: string | null;
  verdict: string | null;
  source: string | null;
  q: string | null;
  origin: string | null;
  stance: string | null;
  raw_format: string | null;
  page: number;
  risk_min: number | null;
  risk_max: number | null;
  risk_null: boolean;
};

const KEYS = [
  "disease",
  "compare",
  "from",
  "to",
  "country",
  "verdict",
  "source",
  "q",
  "origin",
  "stance",
  "raw_format",
  "page",
  "risk_min",
  "risk_max",
  "risk_null",
] as const;

export function emptyFilters(): ObservatoryFilters {
  return {
    disease: null,
    compare: [],
    from: null,
    to: null,
    country: null,
    verdict: null,
    source: null,
    q: null,
    origin: null,
    stance: null,
    raw_format: null,
    page: 1,
    risk_min: null,
    risk_max: null,
    risk_null: false,
  };
}

export function readFilters(params: URLSearchParams): ObservatoryFilters {
  const compare = (params.get("compare") || "")
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
  const page = Math.max(1, Number(params.get("page") || "1") || 1);
  const riskMin = params.get("risk_min");
  const riskMax = params.get("risk_max");
  return {
    disease: params.get("disease"),
    compare,
    from: params.get("from"),
    to: params.get("to"),
    country: params.get("country"),
    verdict: params.get("verdict"),
    source: params.get("source"),
    q: params.get("q"),
    origin: params.get("origin"),
    stance: params.get("stance"),
    raw_format: params.get("raw_format"),
    page,
    risk_min: riskMin != null && riskMin !== "" ? Number(riskMin) : null,
    risk_max: riskMax != null && riskMax !== "" ? Number(riskMax) : null,
    risk_null: params.get("risk_null") === "1" || params.get("risk_null") === "true",
  };
}

export function writeFilters(current: URLSearchParams, patch: Partial<ObservatoryFilters>): URLSearchParams {
  const next = new URLSearchParams(current.toString());
  const merged = { ...readFilters(current), ...patch };
  for (const key of KEYS) {
    next.delete(key);
  }
  if (merged.disease) next.set("disease", merged.disease);
  if (merged.compare.length) next.set("compare", merged.compare.join(","));
  if (merged.from) next.set("from", merged.from);
  if (merged.to) next.set("to", merged.to);
  if (merged.country) next.set("country", merged.country);
  if (merged.verdict) next.set("verdict", merged.verdict);
  if (merged.source) next.set("source", merged.source);
  if (merged.q?.trim()) next.set("q", merged.q.trim());
  if (merged.origin) next.set("origin", merged.origin);
  if (merged.stance) next.set("stance", merged.stance);
  if (merged.raw_format) next.set("raw_format", merged.raw_format);
  if (merged.page > 1) next.set("page", String(merged.page));
  if (merged.risk_min != null) next.set("risk_min", String(merged.risk_min));
  if (merged.risk_max != null) next.set("risk_max", String(merged.risk_max));
  if (merged.risk_null) next.set("risk_null", "1");
  return next;
}

export function filtersToSearch(filters: Partial<ObservatoryFilters>): string {
  const next = writeFilters(new URLSearchParams(), { ...emptyFilters(), ...filters, page: filters.page ?? 1 });
  const raw = next.toString();
  return raw ? `?${raw}` : "";
}

export function filtersToApiQuery(filters: ObservatoryFilters): string {
  const p = new URLSearchParams();
  if (filters.disease) p.set("disease", filters.disease);
  if (filters.compare.length) p.set("compare", filters.compare.join(","));
  if (filters.from) p.set("from", filters.from);
  if (filters.to) p.set("to", filters.to);
  if (filters.country) p.set("country", filters.country);
  if (filters.verdict) p.set("verdict", filters.verdict);
  if (filters.source) p.set("source", filters.source);
  if (filters.q?.trim()) p.set("q", filters.q.trim());
  if (filters.origin) p.set("origin", filters.origin);
  if (filters.stance) p.set("stance", filters.stance);
  if (filters.raw_format) p.set("raw_format", filters.raw_format);
  if (filters.risk_min != null) p.set("risk_min", String(filters.risk_min));
  if (filters.risk_max != null) p.set("risk_max", String(filters.risk_max));
  if (filters.risk_null) p.set("risk_null", "1");
    p.set("order", "published_at");
  return p.toString();
}

export function chipLabel(key: string, value: string): string {
  const names: Record<string, string> = {
    disease: "Enfermedad",
    from: "Desde",
    to: "Hasta",
    country: "País",
    verdict: "Veredicto",
    source: "Fuente",
    q: "Texto",
    origin: "Origen",
    stance: "Postura",
    raw_format: "Formato",
  };
  return `${names[key] || key}: ${value}`;
}

export function activeFilterChips(filters: ObservatoryFilters): { key: keyof ObservatoryFilters; value: string }[] {
  const chips: { key: keyof ObservatoryFilters; value: string }[] = [];
  if (filters.disease) chips.push({ key: "disease", value: filters.disease });
  if (filters.from) chips.push({ key: "from", value: filters.from });
  if (filters.to) chips.push({ key: "to", value: filters.to });
  if (filters.country) chips.push({ key: "country", value: filters.country });
  if (filters.verdict) chips.push({ key: "verdict", value: filters.verdict });
  if (filters.source) chips.push({ key: "source", value: filters.source });
  if (filters.q) chips.push({ key: "q", value: filters.q });
  if (filters.origin) chips.push({ key: "origin", value: filters.origin });
  if (filters.stance) chips.push({ key: "stance", value: filters.stance });
  if (filters.raw_format) chips.push({ key: "raw_format", value: filters.raw_format });
  return chips;
}
