export type Article = {
  content_id: string;
  source_id: string;
  url: string;
  title: string;
  text: string;
  risk_score: number | null;
  verdict: string | null;
  relevance_score: number | null;
  collected_at: string;
  published_at: string | null;
  language?: string | null;
  country?: string | null;
  source_type?: string | null;
  llm_status?: string | null;
  llm_explanation?: string | null;
  llm_provider?: string | null;
  local_explanation?: string | null;
  summary?: string | null;
  raw_format?: string | null;
  disease_tags?: string | null;
  disease_list?: string[];
  explanation_quality?: Quality;
  thumb_url?: string | null;
  thumb_path?: string | null;
  is_news_thumb?: boolean;
};

export type Claim = {
  claim_id: string;
  content_id: string;
  text: string;
  subject: string | null;
  predicate: string | null;
  object: string | null;
  location: string | null;
  animal: string | null;
  nli_label: string | null;
  verifiable: number;
  confidence?: number | null;
};

export type AlertRow = {
  alert_id: string;
  content_id: string;
  risk_score: number;
  verdict: string;
  status: string;
  created_at: string;
  human_label?: string | null;
  title?: string | null;
  article_verdict?: string | null;
  primary_claim?: string | null;
  evidence_snippet?: string | null;
  claims?: Claim[];
  evidence?: EvidenceRow[];
};

export type SourceRow = {
  source_id: string;
  name: string;
  domain: string;
  access_method: string;
  last_checked: string | null;
  last_error: string | null;
  consecutive_failures: number;
  next_check: string | null;
  type?: string | null;
  country?: string | null;
  healthy?: boolean;
  article_count?: number;
  status?: "ok" | "error" | "deferred" | string;
};

export type ImageRow = {
  image_id: string;
  content_id: string;
  storage_key: string;
  cnn_class: string | null;
  cnn_confidence: number | null;
  cnn_scores?: Record<string, number> | null;
  ocr_text: string | null;
  reused: number;
  phash: string | null;
  phash_short?: string | null;
  reuse_label?: string | null;
  reuse_similarity_pct?: number | null;
  reuse_hamming?: number | null;
  encoder?: string | null;
  visual_role?: string | null;
  visual_fusion?: {
    type?: string;
    encoder?: string;
    ocr_text?: string;
    reuse?: boolean;
    reuse_similarity_pct?: number | null;
    animal_health_relevance?: number;
  } | null;
  animal_health_relevance?: number | null;
  file_url?: string | null;
  width?: number | null;
  height?: number | null;
  model_versions?: string | null;
  mime_type?: string | null;
  source_url?: string | null;
  is_news_thumb?: boolean;
};

export type Kpis = {
  articles: number;
  claims: number;
  alerts: number;
  alerts_pending: number;
  images: number;
  sources: number;
  youtube?: number;
  social?: number;
  reviews?: number;
  narratives?: number;
  entities?: number;
  mysql?: boolean;
  backend?: string;
  last_mine?: string | null;
  cnn_samples?: number;
  docs?: number;
  rss?: number;
  seed?: number;
  no_body?: number;
  pct_rss?: number;
  pct_seed?: number;
  pct_no_body?: number;
  by_format?: Record<string, number>;
  mysql_stale?: boolean;
  mysql_lag_seconds?: number | null;
};

export type MineStatus = {
  last_mine?: string | null;
  next_mine?: string | null;
  next_mine_minutes?: number | null;
  interval_seconds?: number;
  articles_new?: number;
  images_processed?: number;
  cnn_samples_new?: number;
  mysql?: boolean;
};

export type Narrative = {
  narrative_id: string;
  label: string;
  claim_count: number;
  growth_pct: number | null;
};

export type DiseaseCard = { id: string; label: string; short?: string; menciones: number };
export type GeoRow = {
  country: string;
  name: string;
  count: number;
  lat?: number;
  lng?: number;
  articles?: { content_id: string; title: string; risk_score?: number | null }[];
  unlocated?: boolean;
};
export type GraphNode = {
  id: string;
  label: string;
  group: string;
  value?: number;
  source_id?: string;
  filter?: Record<string, string | null | undefined>;
};
export type GraphEdge = { from: string; to: string; label?: string };
export type Quality = { score: number; band: string; notes: string[]; llm_used: boolean };
export type ChartFilter = Record<string, string | number | boolean | null | undefined>;
export type ChartDay = {
  day: string;
  count: number;
  missing?: boolean;
  risk_mean?: number | null;
  risk_unknown?: number;
  alerts?: number;
  sample_titles?: string[];
  filter?: ChartFilter;
  [key: string]: string | number | boolean | string[] | ChartFilter | null | undefined;
};
export type ChartBundle = {
  empty?: boolean;
  db_empty?: boolean;
  n?: number;
  articles_without_claims?: number;
  filter?: ChartFilter;
  series?: { id: string; name: string }[];
  volume_by_disease: { id: string; name: string; label: string; count: number; filter?: ChartFilter }[];
  volume_by_origin?: { id: string; name: string; label: string; count: number; filter?: ChartFilter }[];
  volume_by_verdict?: { id: string; name: string; label: string; count: number; filter?: ChartFilter }[];
  volume_by_day: { day: string; count: number }[];
  by_day?: ChartDay[];
  risk_histogram: { bucket: string; count: number; filter?: ChartFilter }[];
  risk_note?: string | null;
  stance: { name: string; value: number; filter?: ChartFilter }[];
  annotations?: { day: string; label: string; kind: string }[];
};
export type EvidenceRow = {
  evidence_id: string;
  claim_id: string;
  url?: string | null;
  source_tier?: string | null;
  snippet?: string | null;
  stance?: string | null;
};
export type CnnMetrics = {
  model_version?: string;
  architecture?: { layer: string; filters?: number; kernel?: string; activation?: string; units?: number; shape?: string; pool?: string }[];
  history?: { acc: number[]; val_acc: number[]; loss: number[]; val_loss: number[] };
  confusion_matrix?: { labels: string[]; matrix: number[][] };
  test_accuracy?: number | null;
  academic_test_accuracy?: number | null;
  experimental_on_synthetic?: boolean;
  production_encoder?: string;
  production_metric?: boolean;
  test_metrics?: { test_accuracy?: number | null; experimental_on_synthetic?: boolean; note?: string };
  samples?: { id: string; class?: string; label_es?: string; url: string; title?: string; origin?: string }[];
  samples_url?: string;
  dataset?: Record<string, number>;
  dataset_total?: number;
  retrain?: string;
  note?: string;
};

export type CnnRealSample = {
  id: string;
  title?: string;
  label_es?: string;
  url: string;
  origin?: string;
  content_id?: string;
  kind?: string;
};

export type CnnPredict = {
  class: string | null;
  label_es?: string;
  confidence: number | null;
  scores: Record<string, number>;
  note?: string;
  encoder?: string;
  role?: string;
  phash?: string;
  phash_short?: string;
  ocr_text?: string;
  animal_health_relevance?: number;
  academic?: {
    class?: string;
    label_es?: string;
    confidence?: number;
    scores?: Record<string, number>;
    note?: string;
    model_version?: string;
  };
  production?: {
    encoder?: string;
    class?: string | null;
    label_es?: string;
    confidence?: number | null;
    scores?: Record<string, number>;
    available?: boolean;
  };
  visual_fusion?: Record<string, unknown>;
};

export type ArticleCard = {
  content_id: string;
  title: string;
  source_id?: string | null;
  verdict?: string | null;
  risk_score?: number | null;
  country?: string | null;
};

export class ArticleNotFoundError extends Error {
  recent: ArticleCard[];
  constructor(id: string, recent: ArticleCard[] = []) {
    super(`article not found: ${id}`);
    this.name = "ArticleNotFoundError";
    this.recent = recent;
  }
}

export const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8010";
const API_TOKEN = import.meta.env.VITE_API_TOKEN || "";

function authHeaders(extra?: HeadersInit): HeadersInit {
  const headers: Record<string, string> = { ...(extra as Record<string, string> | undefined) };
  if (API_TOKEN) headers["X-API-Token"] = String(API_TOKEN);
  return headers;
}

function qs(pathQs?: string) {
  return pathQs ? `?${pathQs}` : "";
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API}${path}`);
  if (!res.ok) throw new Error(`${path} ${res.status}`);
  return res.json();
}

export const api = {
  health: () => get<Record<string, unknown>>("/health"),
  status: () => get<Record<string, unknown>>("/status"),
  kpis: () => get<Kpis>("/kpis"),
  stats: (query = "") =>
    get<{
      kpis: Kpis;
      sparklines: Record<string, number[]>;
      diseases: DiseaseCard[];
      filter: string | null | Record<string, unknown>;
      mysql?: boolean;
      mysql_stale?: boolean;
      mysql_lag_seconds?: number | null;
      last_mine?: string | null;
      mine?: MineStatus;
      cnn_dataset?: Record<string, number>;
      capture?: {
        docs?: number;
        rss?: number;
        seed?: number;
        no_body?: number;
        pct_rss?: number;
        pct_seed?: number;
        pct_no_body?: number;
      };
    }>(`/stats${qs(query)}`),
  charts: (query = "") => get<ChartBundle>(`/charts${qs(query)}`),
  graph: (query = "") =>
    get<{ nodes: GraphNode[]; edges: GraphEdge[]; empty?: boolean; sample?: number; universe?: number }>(
      `/graph${qs(query)}`
    ),
  sources: () => get<{ sources: SourceRow[] }>("/sources"),
  articles: (query = "", page = 1, pageSize = 12) =>
    get<{ articles: Article[]; count: number; page: number; page_size: number }>(
      `/articles?page=${page}&page_size=${pageSize}&thumb_page=${page}&thumb_limit=${pageSize}${query ? `&${query}` : ""}`
    ),
  claims: () => get<{ claims: Claim[] }>("/claims"),
  alerts: (status?: string | null) =>
    get<{ alerts: AlertRow[]; pending: number }>(
      `/alerts${status ? `?status=${encodeURIComponent(status)}&include=article,claims,evidence` : "?include=article,claims,evidence"}`
    ),
  images: (query = "") => get<{ images: ImageRow[] }>(`/images${qs(query)}`),
  narratives: () => get<{ narratives: Narrative[] }>("/narratives"),
  diseases: () => get<{ diseases: DiseaseCard[] }>("/diseases"),
  geo: (query = "") =>
    get<{ countries: GeoRow[]; points: GeoRow[]; unlocated?: GeoRow[] }>(`/geo${qs(query)}`),
  youtube: () => get<{ videos: Article[] }>("/youtube"),
  social: () => get<{ signals: Article[] }>("/social"),
  article: async (id: string) => {
    const res = await fetch(`${API}/articles/${encodeURIComponent(id)}`);
    const body = await res.json().catch(() => ({}));
    if (res.status === 404) {
      throw new ArticleNotFoundError(id, Array.isArray(body?.recent) ? body.recent : []);
    }
    if (!res.ok) throw new Error(`/articles/${id} ${res.status}`);
    return body as {
      article: Article;
      claims: Claim[];
      evidence: EvidenceRow[];
      images: ImageRow[];
      entities_grouped: Record<string, string[]>;
      geo: GeoRow;
      timeline: { at: string; kind: string; label: string; text: string }[];
      similar: { content_id: string; title: string; score: number; reasons: string[] }[];
      graph: { nodes: GraphNode[]; edges: GraphEdge[] };
      quality: Quality;
    };
  },
  cnnMetrics: () => get<CnnMetrics>("/cnn/metrics"),
  cnnSamples: (limit = 12) =>
    get<{ real: boolean; count: number; samples: CnnRealSample[]; empty_message?: string }>(
      `/cnn/samples?real=1&limit=${limit}`
    ),
  cnnPredictFile: async (file: File) => {
    const body = new FormData();
    body.append("file", file);
    const res = await fetch(`${API}/cnn/predict`, { method: "POST", body, headers: authHeaders() });
    if (!res.ok) throw new Error(`cnn/predict ${res.status}`);
    return res.json() as Promise<CnnPredict>;
  },
  cnnPredictSample: async (sampleId: string) => {
    const body = new FormData();
    body.append("sample_id", sampleId);
    const res = await fetch(`${API}/cnn/predict`, { method: "POST", body, headers: authHeaders() });
    if (!res.ok) throw new Error(`cnn/predict ${res.status}`);
    return res.json() as Promise<CnnPredict>;
  },
  cycle: async () => {
    const res = await fetch(`${API}/cycle?demo_seed=false&max_sources=8`, {
      method: "POST",
      headers: authHeaders(),
    });
    if (!res.ok) throw new Error(`cycle ${res.status}`);
    return res.json();
  },
  translate: async (texts: string[]) => {
    const res = await fetch(`${API}/translate`, {
      method: "POST",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ texts }),
    });
    if (!res.ok) throw new Error(`translate ${res.status}`);
    const body = (await res.json()) as { texts?: string[] };
    const out = Array.isArray(body.texts) ? body.texts : [];
    return texts.map((t, i) => (typeof out[i] === "string" ? out[i] : t));
  },
  review: async (alertId: string, human_label: string, reason = "") => {
    const res = await fetch(`${API}/alerts/${alertId}/review`, {
      method: "POST",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ human_label, reason, analyst: "sala" }),
    });
    if (!res.ok) throw new Error(`review ${res.status}`);
    return res.json();
  },
};

export function imageSrc(image: ImageRow | string): string {
  if (typeof image === "object" && image?.image_id) {
    return `${API}/images/${encodeURIComponent(image.image_id)}`;
  }
  const key = String(image || "");
  if (key.startsWith("IMG-") || key.startsWith("/images/")) {
    const id = key.replace("/images/", "");
    return `${API}/images/${encodeURIComponent(id)}`;
  }
  const name = key.split(/[/\\]/).pop() || "";
  return `${API}/files/images/${encodeURIComponent(name)}`;
}

export function thumbSrc(article: { content_id?: string; thumb_url?: string | null } | null | undefined): string | null {
  if (!article?.content_id && !article?.thumb_url) return null;
  const path = article.thumb_url || `/thumbs/${encodeURIComponent(article.content_id || "")}`;
  if (/^https?:\/\//i.test(path)) return path;
  return `${API}${path.startsWith("/") ? path : `/${path}`}`;
}

export function verdictClass(v: string | null | undefined) {
  const x = (v || "").toUpperCase();
  if (x.includes("RESPALD") || x.includes("SUPPORTED")) return "ok";
  if (x.includes("INSUFIC")) return "mid";
  if (x.includes("CONTRAD")) return "bad";
  if (x.includes("ENGAÑ") || x.includes("ENGAN")) return "warn";
  if (x.includes("HUMANA") || x.includes("REVISION")) return "human";
  return "mid";
}
