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
  risk_why?: {
    nli?: string;
    score?: number;
    rule?: string;
    parts?: Record<string, number>;
    parts_named?: { id: string; label: string; value: number }[];
    cross_cut?: { score?: number; reason?: string; peers?: number };
    numeric?: { score?: number; reason?: string; claim?: number | null; official?: number | null };
    hitl?: { label?: string; reason?: string };
    explain?: {
      score?: number;
      formula?: string;
      rows?: { id: string; label: string; value: number; weight: number; contrib: number; why: string }[];
    };
  } | null;
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
  modality?: string | null;
  nli_explain?: {
    label?: string;
    confidence?: number;
    evidence_used?: number;
    supported?: number;
    contradicted?: number;
    official_n?: number;
    formula?: string;
    why?: string;
    items?: {
      url?: string;
      official?: boolean;
      stance?: string;
      claim_tokens?: number;
      overlap?: number;
      overlap_words?: string[];
      anchors?: string[];
      missing?: string[];
    }[];
  };
};

export type AlertRow = {
  alert_id: string;
  content_id: string;
  risk_score: number;
  verdict: string;
  status: string;
  created_at: string;
  human_label?: string | null;
  human_reason?: string | null;
  title?: string | null;
  article_verdict?: string | null;
  primary_claim?: string | null;
  evidence_snippet?: string | null;
  contrast?: {
    status?: "hit" | "partial" | "peer" | "none" | string;
    stance?: string | null;
    snippet?: string | null;
    url?: string | null;
    title?: string | null;
    why?: string | null;
    facts?: string[];
    peers?: { title?: string; content_id?: string }[];
  };
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
  language?: string | null;
  priority?: string | null;
  frequency_minutes?: number | null;
  active?: boolean | number;
  healthy?: boolean;
  article_count?: number;
  evidence_uses?: number;
  rss_url?: string | null;
  base_url?: string | null;
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

export type KeywordTerm = {
  term_id: string;
  term: string;
  category: string;
  label?: string | null;
  weight: number;
  active: number;
};

export type NarrativeDossier = {
  narrative_id: string;
  label: string;
  description?: string;
  volume: number;
  growth_pct: number;
  state?: string;
  state_label?: string;
  first_seen?: string | null;
  last_seen?: string | null;
  country_n?: number;
  sources_n?: number;
  claims_n?: number;
  priority?: { code: string; label: string; why: string };
  contrast_level?: { level: number; label: string };
  classification?: { code: string; label: string; why: string; human_priority?: boolean };
  series?: { day: string; count: number }[];
  semantic_stages?: { stage: number; from?: string; to?: string; publications: number; concepts: string[] }[];
  propagation?: { country: string; first_seen?: string | null; publications: number; sources: number; peak?: string | null }[];
  source_propagation?: { source_id: string; name: string; country?: string; publications: number; first_seen?: string | null; last_seen?: string | null }[];
  articles?: { content_id: string; title?: string; published_at?: string; country?: string }[];
  claims?: Claim[];
  evidence?: (EvidenceRow & { host?: string; official?: boolean })[];
  contrast?: NarrativeAnalysis["contrast"];
  origin_note?: string;
};

export type NarrativeOverview = {
  principle: string;
  method: { id: string; title: string; text: string }[];
  sample: number;
  cloud: { term: string; count: number }[];
  categories: { id: string; label: string; count: number }[];
  pairs: {
    a: string;
    b: string;
    a_label: string;
    b_label: string;
    count: number;
    force: number;
    relation: string;
  }[];
  structures: { label: string; count: number }[];
  graph: { nodes: GraphNode[]; edges: GraphEdge[]; empty?: boolean };
  bank: Record<string, { label: string; terms: string[]; weight?: number }>;
  clusters?: Narrative[];
  narratives?: NarrativeDossier[];
  alerts?: { narrative_id: string; label: string; growth_pct: number; reason: string; priority?: { code: string; label: string } }[];
  kpis?: Record<string, number>;
  sources?: SourceRow[];
  sources_available?: number;
  sources_used?: number;
};

export type NarrativeAnalysis = {
  principle: string;
  signals: {
    sentence: string;
    modality: string;
    modality_label: string;
    hits: { category: string; term: string; label: string }[];
    note: string;
    not_a_verdict: boolean;
  }[];
  claims: { text: string; modality: string; parent: string }[];
  pairs: { a_label: string; b_label: string; force: number; count: number }[];
  structures: { label: string; sentence: string; note: string }[];
  contrast?: {
    afirmacion: string;
    evidencia_afirmacion: string;
    evidencia_externa: { title?: string; url?: string; host?: string }[];
    informacion_oficial: { title?: string; url?: string; host?: string }[];
    contradicciones: { text?: string; nli?: string }[];
    no_comprobado: { text?: string; nli?: string }[];
    normativa?: string | null;
    conclusion: { code: string; label: string; why: string; human_priority?: boolean };
  };
  classification?: { code: string; label: string; why: string; human_priority?: boolean };
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
  place_id?: string;
  grain?: "place" | "country";
  query?: string | null;
  disease?: string | null;
  diseases?: string[];
  risk_mean?: number | null;
  first_seen?: string | null;
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

const _api = import.meta.env.VITE_API_URL as string | undefined;
export const API = _api === "" ? "" : _api || "http://127.0.0.1:8010";
const API_TOKEN = import.meta.env.VITE_API_TOKEN || "";

function authHeaders(extra?: HeadersInit): HeadersInit {
  const headers: Record<string, string> = { ...(extra as Record<string, string> | undefined) };
  if (API_TOKEN) headers["X-API-Token"] = String(API_TOKEN);
  return headers;
}

function qs(pathQs?: string) {
  return pathQs ? `?${pathQs}` : "";
}

async function readError(res: Response, fallback: string): Promise<string> {
  const body = await res.json().catch(() => ({} as { detail?: unknown }));
  const detail = (body as { detail?: unknown }).detail;
  if (typeof detail === "string" && detail.trim()) return detail.trim();
  return `${fallback} ${res.status}`;
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API}${path}`, { headers: authHeaders() });
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
  articles: (query = "", page = 1, pageSize = 12) => {
    const params = new URLSearchParams(query);
    if (!params.has("order")) params.set("order", "published_at");
    const extra = params.toString();
    return get<{ articles: Article[]; count: number; page: number; page_size: number }>(
      `/articles?page=${page}&page_size=${pageSize}&thumb_page=${page}&thumb_limit=${pageSize}${extra ? `&${extra}` : ""}`
    );
  },
  narratives: () => get<{ narratives: Narrative[] }>("/narratives"),
  narrativesOverview: (query = "") => get<NarrativeOverview>(`/narratives/overview${qs(query)}`),
  narrative: (id: string) => get<NarrativeOverview & { narrative: NarrativeDossier }>(`/narratives/${encodeURIComponent(id)}`),
  reviewNarrative: async (id: string, human_label: string, reason = "") => {
    const res = await fetch(`${API}/narratives/${encodeURIComponent(id)}/review`, {
      method: "POST",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ human_label, reason, analyst: "sala" }),
    });
    if (!res.ok) throw new Error(await readError(res, "No se pudo guardar la revisión"));
    return res.json();
  },
  claims: (query = "") => get<{ claims: Claim[]; count: number }>(`/claims${qs(query)}`),
  evidence: () => get<{ evidence: (EvidenceRow & { claim_text?: string; content_id?: string })[]; count: number }>("/evidence"),
  bankTerms: () => get<{ terms: KeywordTerm[]; principle?: string }>("/banks/terms"),
  saveTerm: async (row: Partial<KeywordTerm>) => {
    const path = row.term_id ? `/banks/terms/${encodeURIComponent(row.term_id)}` : "/banks/terms";
    const res = await fetch(`${API}${path}`, {
      method: row.term_id ? "PATCH" : "POST",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify(row),
    });
    if (!res.ok) throw new Error(await readError(res, "No se pudo guardar el término"));
    return res.json();
  },
  deleteTerm: async (id: string) => {
    const res = await fetch(`${API}/banks/terms/${encodeURIComponent(id)}`, { method: "DELETE", headers: authHeaders() });
    if (!res.ok) throw new Error(await readError(res, "No se pudo borrar el término"));
    return res.json();
  },
  saveSource: async (row: Partial<SourceRow> & { source_id?: string }, create = false) => {
    const path = create || !row.source_id ? "/sources" : `/sources/${encodeURIComponent(row.source_id)}`;
    const res = await fetch(`${API}${path}`, {
      method: create || !row.source_id ? "POST" : "PATCH",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify(row),
    });
    if (!res.ok) throw new Error(await readError(res, "No se pudo guardar la fuente"));
    return res.json();
  },
  alerts: (status?: string | null, include = true) => {
    const params = new URLSearchParams();
    if (status) params.set("status", status);
    if (include) params.set("include", "article,claims,evidence");
    const q = params.toString();
    return get<{ alerts: AlertRow[]; pending: number; count: number }>(`/alerts${q ? `?${q}` : ""}`);
  },
  images: (query = "") => get<{ images: ImageRow[] }>(`/images${qs(query)}`),
  diseases: () => get<{ diseases: DiseaseCard[] }>("/diseases"),
  geo: (query = "") =>
    get<{ countries: GeoRow[]; points: GeoRow[]; unlocated?: GeoRow[] }>(`/geo${qs(query)}`),
  youtube: () => get<{ videos: Article[] }>("/youtube"),
  social: () => get<{ signals: Article[] }>("/social"),
  article: async (id: string) => {
    const res = await fetch(`${API}/articles/${encodeURIComponent(id)}`, { headers: authHeaders() });
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
      narrative?: NarrativeAnalysis | null;
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
    const res = await fetch(`${API}/cycle?demo_seed=false`, {
      method: "POST",
      headers: authHeaders(),
    });
    if (!res.ok) throw new Error(`cycle ${res.status}`);
    return res.json();
  },
  translate: async (texts: string[], signal?: AbortSignal) => {
    const res = await fetch(`${API}/translate`, {
      method: "POST",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ texts }),
      signal,
    });
    if (!res.ok) throw new Error(`translate ${res.status}`);
    const body = (await res.json()) as { texts?: string[] };
    const out = Array.isArray(body.texts) ? body.texts : [];
    return texts.map((t, i) => (typeof out[i] === "string" ? out[i] : t));
  },
  review: async (alertId: string, human_label: string, reason = "") => {
    const res = await fetch(`${API}/alerts/${encodeURIComponent(alertId)}/review`, {
      method: "POST",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ human_label, reason, analyst: "sala" }),
    });
    if (!res.ok) throw new Error(await readError(res, "No se pudo guardar la revisión"));
    return res.json() as Promise<{ ok: boolean; alert: AlertRow }>;
  },
  reviewArticle: async (contentId: string, human_label: string, reason = "") => {
    const res = await fetch(`${API}/articles/${encodeURIComponent(contentId)}/review`, {
      method: "POST",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ human_label, reason, analyst: "sala" }),
    });
    if (!res.ok) throw new Error(await readError(res, "No se pudo guardar la revisión"));
    return res.json() as Promise<{ ok: boolean; alert: AlertRow; article?: Article }>;
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
