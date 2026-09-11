import type { Article, ImageRow } from "./api";

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

export function sourceInitials(name?: string | null): string {
  const clean = (name || "Fuente").replace(/^www\./, "").trim();
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

export function shortChartDate(iso?: string | null): string {
  if (!iso || iso === "—" || iso === "Sin fecha") return iso || "Sin fecha";
  const raw = iso.length === 10 ? `${iso}T12:00:00` : iso;
  const d = new Date(raw);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("es-MX", { day: "numeric", month: "short" });
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
  if (mapped && !mapped.startsWith("SRC-")) return mapped;
  const raw = (article.url || "").trim();
  if (raw.startsWith("http://") || raw.startsWith("https://")) {
    try {
      return new URL(raw).hostname.replace(/^www\./, "");
    } catch {
      /* ignore */
    }
  }
  const st = (article.source_type || "").trim();
  if (st && !/^src-/i.test(st)) return st;
  return mapped || article.source_id || "Fuente";
}

export const KIND_LABEL: Record<SourceKind, string> = {
  oficial: "Oficial",
  youtube: "YouTube",
  social: "Redes",
  cientifico: "Científico",
  prensa: "Prensa",
};

export function twoLineSummary(text?: string | null, title?: string | null): string {
  const raw = (text || "").replace(/\s+/g, " ").trim();
  if (!raw || raw === (title || "").trim()) return "";
  return raw.length > 220 ? `${raw.slice(0, 217)}…` : raw;
}

/** Longer excerpt for sala cards; visual clamp + Leer más hide the rest. */
export function cardExcerpt(text?: string | null, title?: string | null, max = 560): string {
  const raw = (text || "").replace(/\s+/g, " ").trim();
  if (!raw || raw === (title || "").trim()) return "";
  return raw.length > max ? `${raw.slice(0, max - 1)}…` : raw;
}

export function flowText(text?: string | null): string {
  return (text || "").replace(/\s+/g, " ").trim();
}

export function formatDate(iso?: string | null): string {
  if (!iso) return "Sin fecha";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) {
    const cut = iso.slice(0, 10);
    return cut || "Sin fecha";
  }
  return d.toLocaleDateString("es-MX", { day: "numeric", month: "short", year: "numeric" });
}

export function verdictLabel(v?: string | null): string {
  const x = (v || "").trim();
  if (!x) return "Sin veredicto";
  const up = x.toUpperCase();
  if (up.includes("RESPALD") || up === "SUPPORTED") return "Respaldado";
  if (up.includes("INSUFIC")) return "Insuficiente";
  if (up.includes("CONTRAD") || up === "CONTRADICTED") return "Contradicho";
  if (up.includes("ENGAÑ") || up.includes("ENGAN") || up.includes("MISLEAD")) return "Posiblemente engañoso";
  if (up.includes("HUMANA") || up.includes("REVISION") || up.includes("REVIEW")) return "Revisión humana";
  if (up.includes("UNKNOWN") || up === "SIN VERIFICAR") return "Sin verificar";
  return x;
}

export function stanceLabel(v?: string | null): string {
  const x = (v || "").trim();
  if (!x) return "Sin postura";
  const up = x.toUpperCase();
  if (up === "SUPPORTED" || up.includes("RESPALD")) return "Respaldado";
  if (up === "CONTRADICTED" || up.includes("CONTRAD")) return "Contradicho";
  if (up === "UNKNOWN") return "Sin verificar";
  return x;
}

export function entityKindLabel(kind: string): string {
  const map: Record<string, string> = {
    DISEASE: "Enfermedad",
    ANIMAL: "Animal",
    COUNTRY: "País",
    ORG: "Organización",
  };
  return map[kind] || kind;
}

export function riskTone(score: number | null | undefined): "low" | "mid" | "high" {
  const n = Number(score);
  if (!Number.isFinite(n)) return "mid";
  if (n >= 70) return "high";
  if (n >= 40) return "mid";
  return "low";
}
