import type { Article, ImageRow } from "./api";
import { lookup, type Lang } from "./i18n";

export type SourceKind = "oficial" | "youtube" | "social" | "cientifico" | "prensa";

const SYNTHETIC_MARKERS = ["models/cnn", "cnn/dataset", "cnn\\dataset"];

export function isCnnFakeThumb(image?: ImageRow | null): boolean {
  if (!image) return false;
  const key = (image.storage_key || "").replace(/\\/g, "/").toLowerCase();
  const src = (image.source_url || "").replace(/\\/g, "/").toLowerCase();
  if (SYNTHETIC_MARKERS.some((m) => key.includes(m.replace(/\\/g, "/")) || src.includes(m.replace(/\\/g, "/")))) {
    return true;
  }
  const name = (key.split("/").pop() || "") + " " + (src.split("/").pop() || "");
  if (name.includes("ph_") || name.endsWith(".svg")) return false;
  return name.includes("corpus_") || name.includes("fb_") || name.includes("demo_seed_");
}

export function isRealNewsThumb(image?: ImageRow | null): boolean {
  if (!image || isCnnFakeThumb(image)) return false;
  if (image.is_news_thumb === false) return false;
  if (image.is_news_thumb === true) return true;
  const mime = (image.mime_type || "").toLowerCase();
  if (mime.includes("svg") || (image.storage_key || "").includes("ph_")) return false;
  if (mime && !["jpeg", "jpg", "png", "webp", "svg"].some((t) => mime.includes(t))) return false;
  if (/^https?:\/\//i.test(image.source_url || "")) return true;
  return Boolean(image.image_id && image.storage_key);
}

export function youtubeThumbUrl(url?: string | null): string | null {
  if (!url) return null;
  const match = String(url).match(
    /(?:youtube\.com\/(?:watch\?v=|embed\/|shorts\/|live\/)|youtu\.be\/)([A-Za-z0-9_-]{11})/i
  );
  return match ? `https://img.youtube.com/vi/${match[1]}/hqdefault.jpg` : null;
}

export function sourceInitials(name?: string | null, lang: Lang = "es"): string {
  const clean = (name || lookup(lang, "common.source")).replace(/^www\./, "").trim();
  const parts = clean.split(/[\s./_-]+/).filter((p) => /[a-z0-9]/i.test(p));
  const a = parts[0]?.[0] || "N";
  const b = parts[1]?.[0] || parts[0]?.[1] || "";
  return (a + b).toUpperCase();
}

export function primaryDisease(article: Article): string {
  const listed = (article.disease_list || []).map((d) => String(d).trim()).filter(Boolean);
  if (listed[0]) return listed[0];
  const blob = `${article.title || ""} ${article.text || ""} ${article.url || ""}`.toLowerCase();
  if (blob.includes("gusano") || blob.includes("screwworm") || blob.includes("barrenador")) return "gusano_barrenador";
  if (blob.includes("porcina") || blob.includes("ppc") || blob.includes("swine fever") || blob.includes("peste porcina")) {
    return "fiebre_porcina_clasica";
  }
  if (blob.includes("aviar") || blob.includes("h5n1") || blob.includes("h5n") || blob.includes("avian")) return "gripe_aviar";
  return "";
}

export const DISEASE_VISUAL: Record<string, { label: string; hue: string }> = {
  gusano_barrenador: { label: "Gusano barrenador", hue: "#14532d" },
  gripe_aviar: { label: "Gripe aviar", hue: "#1e3a5f" },
  fiebre_porcina_clasica: { label: "PPC", hue: "#4a1942" },
};

export const MAP_DISEASE_COLOR: Record<string, { fill: string; stroke: string; label: string }> = {
  gusano_barrenador: { fill: "#2dd4bf", stroke: "#99f6e4", label: "Gusano barrenador" },
  gripe_aviar: { fill: "#38bdf8", stroke: "#bae6fd", label: "Gripe aviar" },
  fiebre_porcina_clasica: { fill: "#c084fc", stroke: "#e9d5ff", label: "PPC" },
};

export function mapDiseaseStyle(disease?: string | null, lang: Lang = "es") {
  const base = MAP_DISEASE_COLOR[disease || ""];
  if (!base) return { fill: "#94a3b8", stroke: "#cbd5e1", label: lookup(lang, "disease.mixed") };
  const key =
    disease === "gusano_barrenador"
      ? "disease.gusano"
      : disease === "gripe_aviar"
        ? "disease.aviar"
        : disease === "fiebre_porcina_clasica"
          ? "disease.ppc"
          : "";
  return { ...base, label: key ? lookup(lang, key) : base.label };
}

export function diseaseUiLabel(id?: string | null, fallback?: string, lang: Lang = "es"): string {
  if (id === "gusano_barrenador") return lookup(lang, "disease.gusano");
  if (id === "gripe_aviar") return lookup(lang, "disease.aviar");
  if (id === "fiebre_porcina_clasica") return lookup(lang, "disease.ppc");
  if (id === "otras") return lookup(lang, "filter.other");
  return fallback || lookup(lang, "disease.mixed");
}

export function riskHint(score?: number | null, lang: Lang = "es") {
  if (score == null || Number.isNaN(score)) return lookup(lang, "map.risk.none");
  const n = Math.round(score);
  if (n >= 70) return lookup(lang, "map.risk.high", { n });
  if (n >= 40) return lookup(lang, "map.risk.mid", { n });
  return lookup(lang, "map.risk.low", { n });
}

export function shortChartDate(iso?: string | null, lang: Lang = "es"): string {
  const none = lookup(lang, "date.none");
  if (!iso || iso === "—" || iso === "Sin fecha" || iso === "No date") return iso || none;
  const raw = iso.length === 10 ? `${iso}T12:00:00` : iso;
  const d = new Date(raw);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString(lang === "en" ? "en-US" : "es-MX", { day: "numeric", month: "short" });
}

export function sourceKind(article: Article): SourceKind {
  const url = (article.url || "").toLowerCase();
  const type = `${article.source_type || ""} ${article.raw_format || ""}`.toLowerCase();
  const title = `${article.title || ""} ${article.text || ""}`.toLowerCase();
  if (url.includes("youtube") || url.includes("youtu.be") || type.includes("youtube")) return "youtube";
  if (
    url.includes("openalex.org") ||
    url.includes("pubmed") ||
    url.includes("doi.org") ||
    title.includes("pubmed") ||
    title.includes("openalex") ||
    type.includes("cientif") ||
    type.includes("investig")
  ) {
    return "cientifico";
  }
  if (
    url.includes("woah.org") ||
    url.includes("oie.int") ||
    url.includes("senasica") ||
    url.includes("gob.mx") ||
    url.includes("fao.org") ||
    url.includes("who.int") ||
    url.includes("cdc.gov") ||
    url.includes("usda.gov") ||
    title.includes("official portal") ||
    title.includes("senasica") ||
    type.includes("oficial")
  ) {
    return "oficial";
  }
  if (
    url.includes("twitter.com") ||
    url.includes("x.com") ||
    url.includes("facebook.com") ||
    url.includes("linkedin.com") ||
    url.includes("reddit.com") ||
    type.includes("social") ||
    type.includes("twitter") ||
    type.includes("linkedin") ||
    type.includes("facebook")
  ) {
    return "social";
  }
  return "prensa";
}

export function displaySourceName(article: Article, mapped?: string | null): string {
  const raw = (article.url || "").trim();
  if (raw.startsWith("http://") || raw.startsWith("https://")) {
    try {
      const host = new URL(raw).hostname.replace(/^www\./, "");
      if (host && !host.includes("gdeltproject.org")) return host;
    } catch {
      /* ignore */
    }
  }
  if (mapped && !mapped.startsWith("SRC-")) return mapped;
  const st = (article.source_type || "").trim();
  if (st && !/^src-/i.test(st)) return st;
  return mapped || article.source_id || lookup("es", "common.source");
}

export const KIND_LABEL: Record<SourceKind, string> = {
  oficial: "Oficial",
  youtube: "YouTube",
  social: "Redes",
  cientifico: "Científico",
  prensa: "Prensa",
};

export function kindLabel(kind: SourceKind, lang: Lang = "es"): string {
  return lookup(lang, `origin.${kind}`);
}

export function twoLineSummary(text?: string | null, title?: string | null): string {
  return cardExcerpt(text, title, 160);
}

const GDELT_NOISE =
  /\b(avian influenza|h5n1|hpai|screwworm|senasica|woah|classical swine fever|gusano barrenador|gripe aviar)\b/gi;

/** Recorte corto para sala. Tira título repetido y el relleno de GDELT. */
export function cardExcerpt(text?: string | null, title?: string | null, max = 180): string {
  let raw = (text || "").replace(/\s+/g, " ").trim();
  const t = (title || "").replace(/\s+/g, " ").trim();
  if (!raw) return "";
  if (t && raw.toLowerCase().startsWith(t.toLowerCase())) {
    raw = raw.slice(t.length).replace(/^[\s.:;,—-]+/, "");
  }
  raw = raw.replace(/^«[^»]+»\s*(es un documento[^.]*\.)?\s*/i, "");
  raw = raw.replace(/\b\d{8}T\d+\S*/g, " ").replace(GDELT_NOISE, " ");
  raw = raw.replace(/\b[\w.-]+\.(com|org|net|gov|edu|mx)\b/gi, " ");
  raw = raw.replace(/\s+/g, " ").trim();
  if (!raw || raw.toLowerCase() === t.toLowerCase()) return "";
  if (raw.length < 48) return "";
  return raw.length > max ? `${raw.slice(0, max - 1)}…` : raw;
}

export function articleLede(text?: string | null, title?: string | null): string {
  return cardExcerpt(text, title, 320);
}

export function flowText(text?: string | null): string {
  return (text || "").replace(/\s+/g, " ").trim();
}

export function displayClaim(text?: string | null, title?: string | null): string {
  const leftover = cardExcerpt(text, title, 280);
  if (leftover) return leftover;
  const t = (title || "").replace(/\s+/g, " ").trim();
  return t || flowText(text);
}

export function riskHeadline(why?: Article["risk_why"] | null, score?: number | null): string {
  const rule = riskRuleLabel(why?.rule);
  if (rule) return `${rule}.`;
  const rows = why?.explain?.rows || [];
  const top = [...rows].sort((a, b) => Number(b.contrib) - Number(a.contrib))[0];
  if (top && Number(top.contrib) > 0) {
    return `Lo que más pesa: ${String(top.label || "").toLowerCase()}.`;
  }
  if (score != null) return `Riesgo ${score}/100 según seis señales.`;
  return "";
}

export function formatDate(iso?: string | null, lang: Lang = "es"): string {
  const none = lookup(lang, "date.none");
  const loc = lang === "en" ? "en-US" : "es-MX";
  if (!iso) return none;
  const raw = iso.trim().replace(/Z$/i, "");
  const compact = raw.match(/^(\d{4})(\d{2})(\d{2})(?:T\d*)?/);
  if (compact) {
    const d = new Date(`${compact[1]}-${compact[2]}-${compact[3]}T12:00:00`);
    if (!Number.isNaN(d.getTime())) {
      return d.toLocaleDateString(loc, { day: "numeric", month: "short", year: "numeric" });
    }
  }
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) {
    const cut = iso.slice(0, 10);
    return cut.includes("-") ? cut : none;
  }
  return d.toLocaleDateString(loc, { day: "numeric", month: "short", year: "numeric" });
}

export function formatPublishedAt(published?: string | null, lang: Lang = "es"): string {
  const raw = (published || "").trim();
  if (!raw) return lookup(lang, "date.noPub");
  return formatDate(raw, lang);
}

const PART_LABELS: Record<string, string> = {
  evidence_contradiction: "discrepancia con evidencia oficial",
  source_reliability: "fiabilidad de la fuente",
  image_reuse: "imagen reusada",
  claim_severity: "gravedad de la afirmación",
  narrative_growth: "narrativa en crecimiento",
  visual_anomaly: "anomalía visual",
};

const IMAGE_CLASS_ES: Record<string, string> = {
  OFFICIAL_DOCUMENT: "documento oficial",
  NEWS_SCREENSHOT: "captura de noticia",
  SOCIAL_MEDIA: "captura de red social",
  MEME: "meme",
  INFOGRAPHIC: "infografía",
  ANIMAL_HEALTH_CONTENT: "imagen de enfermedad animal",
  PHOTOGRAPH: "fotografía",
  POTENTIALLY_MANIPULATED: "posible manipulación",
};

function encoderWhy(encoder?: string | null): string {
  const enc = (encoder || "").toLowerCase();
  if (enc.includes("clip")) return "CLIP compara la foto con 8 descripciones de tipo de imagen";
  if (enc.includes("resnet")) return "ResNet (ImageNet) asigna un tipo visual";
  if (enc.includes("url")) return "una heurística por el dominio de la URL, sin mirar los píxeles";
  if (enc.includes("academic")) return "la CNN académica experimental (dibujos 64×64)";
  return "el clasificador de imagen";
}

export function riskWhyText(
  why?: Article["risk_why"] | null,
  score?: number | null,
): string {
  const n = why?.score ?? score;
  if (n == null && !why) return "";
  const named =
    why?.parts_named && why.parts_named.length
      ? why.parts_named
      : Object.entries(why?.parts || {}).map(([id, value]) => ({
          id,
          label: PART_LABELS[id] || id,
          value,
        }));
  const top = [...named]
    .filter((p) => Number(p.value) >= 8)
    .sort((a, b) => Number(b.value) - Number(a.value))
    .slice(0, 3);
  const bits: string[] = [];
  if (n != null) {
    bits.push(
      `Riesgo ${n}/100: no es un % de que la noticia sea falsa. Es la suma ponderada de seis señales (evidencia, fuente, reuso de imagen, gravedad, narrativa y visual).`,
    );
  }
  if (top.length) {
    bits.push(
      `Lo que más sube el número: ${top
        .map((p) => `${(PART_LABELS[p.id] || p.label || p.id).toLowerCase()} (${Math.round(Number(p.value))})`)
        .join(", ")}.`,
    );
  }
  const rule = riskRuleLabel(why?.rule);
  if (rule) bits.push(rule + ".");
  if (why?.hitl?.label) {
    bits.push(`Un analista lo marcó como ${why.hitl.label}${why.hitl.reason ? ` (${why.hitl.reason})` : ""}.`);
  }
  return bits.join(" ");
}

export function cnnConfidenceWhy(image: {
  cnn_class?: string | null;
  cnn_confidence?: number | null;
  cnn_scores?: Record<string, number> | null;
  encoder?: string | null;
}): string {
  if (image.cnn_confidence == null && !image.cnn_class) return "";
  const pct = Math.round(Number(image.cnn_confidence || 0) * 100);
  const klass = IMAGE_CLASS_ES[image.cnn_class || ""] || (image.cnn_class || "sin clase").toLowerCase();
  const ranked = Object.entries(image.cnn_scores || {}).sort((a, b) => b[1] - a[1]);
  const second = ranked[1];
  const bits = [
    `Confianza ${pct}% en «${klass}»: ${encoderWhy(image.encoder)} y reparte 100 puntos entre 8 tipos; esta clase se quedó ${pct}.`,
  ];
  if (second) {
    const sp = Math.round(second[1] * 100);
    const sl = IMAGE_CLASS_ES[second[0]] || second[0].toLowerCase();
    const gap = pct - sp;
    bits.push(`La segunda fue «${sl}» (${sp}%).`);
    if (gap >= 40) bits.push("El margen es amplio, el tipo de imagen está bastante claro.");
    else if (gap <= 12) bits.push("El margen es estrecho: otra clase casi empata.");
  }
  bits.push("Ese % no dice si el hecho es verdadero.");
  return bits.join(" ");
}

export function claimConfidenceWhy(confidence?: number | null, nli?: string | null): string {
  if (confidence == null) return "";
  const pct = Math.round(Number(confidence) * 100);
  const stance = stanceLabel(nli).toLowerCase();
  return `Confianza ${pct}% en la postura «${stance}»: sale del cruce léxico de la afirmación con fichas oficiales (WOAH, SENASICA, etc.). No es un detector de fake news.`;
}

export function verdictLabel(v?: string | null, lang: Lang = "es"): string {
  const x = (v || "").trim();
  if (!x) return lookup(lang, "verdict.empty");
  const up = x.toUpperCase();
  if (up.includes("RESPALD") || up === "SUPPORTED") return lookup(lang, "verdict.respaldado");
  if (up.includes("INSUFIC")) return lookup(lang, "verdict.insuficiente");
  if (up.includes("CONTRAD") || up === "CONTRADICTED") return lookup(lang, "verdict.contradicho");
  if (up.includes("ENGAÑ") || up.includes("ENGAN") || up.includes("MISLEAD")) return lookup(lang, "verdict.enganoso");
  if (up.includes("HUMANA") || up.includes("REVISION") || up.includes("REVIEW")) return lookup(lang, "verdict.humana");
  if (up.includes("UNKNOWN") || up === "SIN VERIFICAR" || up.includes("UNVERIF")) return lookup(lang, "verdict.sin");
  return x;
}

export function riskRuleLabel(rule?: string | null, lang: Lang = "es"): string {
  const key = `rule.${rule || ""}`;
  const hit = lookup(lang, key);
  return hit === key ? "" : hit;
}

export function stanceLabel(v?: string | null, lang: Lang = "es"): string {
  const x = (v || "").trim();
  if (!x) return lookup(lang, "stance.empty");
  const up = x.toUpperCase();
  if (up === "SUPPORTED" || up.includes("RESPALD")) return lookup(lang, "verdict.respaldado");
  if (up === "CONTRADICTED" || up.includes("CONTRAD")) return lookup(lang, "verdict.contradicho");
  if (up === "UNKNOWN") return lookup(lang, "verdict.sin");
  return x;
}

export function entityKindLabel(kind: string, lang: Lang = "es"): string {
  const key = `entity.${kind}`;
  const hit = lookup(lang, key);
  return hit === key ? kind : hit;
}

export function riskTone(score: number | null | undefined): "low" | "mid" | "high" {
  const n = Number(score);
  if (!Number.isFinite(n)) return "mid";
  if (n >= 70) return "high";
  if (n >= 40) return "mid";
  return "low";
}
