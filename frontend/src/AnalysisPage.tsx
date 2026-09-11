import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  api,
  imageSrc,
  thumbSrc,
  verdictClass,
  ArticleNotFoundError,
  type AlertRow,
  type ArticleCard,
  type Claim,
  type EvidenceRow,
  type ImageRow,
  type Quality,
} from "./api";
import AppHeader from "./components/AppHeader";
import { SoftmaxBars } from "./components/ImageCard";
import LeerMas from "./components/LeerMas";
import MapView from "./components/MapView";
import { HitlButtons } from "./Observatory";
import SafeImg from "./components/SafeImg";
import {
  KIND_LABEL,
  displaySourceName,
  entityKindLabel,
  flowText,
  formatDate,
  isRealNewsThumb,
  riskTone,
  sourceKind,
  youtubeThumbUrl,
  stanceLabel,
  verdictLabel,
} from "./display";
import { hydratePoint } from "./geoCentroids";
import { isAllowlistedHttp, articleHref } from "./safeUrl";
import { useTranslated } from "./translate";

const OFFICIAL_HOST_LABEL: Record<string, string> = {
  "woah.org": "WOAH",
  "cdc.gov": "CDC",
  "aphis.usda.gov": "USDA APHIS",
  "usda.gov": "USDA",
  "fao.org": "FAO",
  "who.int": "OMS",
  "paho.org": "OPS/OMS",
  "gob.mx": "SENASICA",
};

function evidenceHost(url?: string | null): string {
  try {
    const host = new URL(url || "").hostname.replace(/^www\./, "").toLowerCase();
    return host;
  } catch {
    return "";
  }
}

function officialLabel(url?: string | null): string {
  const host = evidenceHost(url);
  if (!host) return "Fuente oficial";
  for (const [suffix, label] of Object.entries(OFFICIAL_HOST_LABEL)) {
    if (host === suffix || host.endsWith("." + suffix)) return label;
  }
  return host;
}

function uniqueOfficialSources(rows: EvidenceRow[], limit = 4): EvidenceRow[] {
  const seenUrl = new Set<string>();
  const seenHost = new Set<string>();
  const out: EvidenceRow[] = [];
  for (const row of rows) {
    const url = (row.url || "").trim();
    const key = url.replace(/\/+$/, "").toLowerCase() || row.evidence_id;
    if (seenUrl.has(key)) continue;
    const host = evidenceHost(url);
    if (host && seenHost.has(host)) continue;
    seenUrl.add(key);
    if (host) seenHost.add(host);
    out.push(row);
    if (out.length >= limit) break;
  }
  return out;
}

export default function AnalysisPage() {
  const { id = "" } = useParams();
  const [data, setData] = useState<any>(null);
  const [err, setErr] = useState("");
  const [recent, setRecent] = useState<ArticleCard[]>([]);
  const [hitlNote, setHitlNote] = useState("");
  const [hitlBusy, setHitlBusy] = useState(false);
  const [modReason, setModReason] = useState("");
  const [modOpen, setModOpen] = useState(false);
  const [openClaimId, setOpenClaimId] = useState<string | null>(null);

  async function reload() {
    const payload = await api.article(id);
    setData(payload);
  }

  useEffect(() => {
    let cancelled = false;
    setData(null);
    setErr("");
    setRecent([]);
    setOpenClaimId(null);
    (async () => {
      try {
        const payload = await api.article(id);
        if (!cancelled) setData(payload);
      } catch (e) {
        let extra: ArticleCard[] = e instanceof ArticleNotFoundError ? e.recent : [];
        if (!extra.length) {
          try {
            const list = await api.articles("", 1, 5);
            extra = (list.articles || []).slice(0, 5).map((a) => ({
              content_id: a.content_id,
              title: a.title || a.url || a.content_id,
              source_id: a.source_id,
              verdict: a.verdict,
              risk_score: a.risk_score,
              country: a.country,
            }));
          } catch {
            extra = [];
          }
        }
        if (!cancelled) {
          setErr("No se encontró el artículo");
          setRecent(extra.slice(0, 5));
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [id]);

  const article = data?.article;
  const source = data?.source;
  const claims: Claim[] = data?.claims || [];
  const evidence: EvidenceRow[] = data?.evidence || [];
  const images: ImageRow[] = data?.images || [];
  const grouped: Record<string, string[]> = data?.entities_grouped || {};
  const quality: Quality | undefined = data?.quality || article?.explanation_quality;
  const geo = data?.geo ? hydratePoint(data.geo) : null;
  const timeline = data?.timeline || [];
  const similar = data?.similar || [];
  const alerts: AlertRow[] = (data?.alerts || []).filter((a: AlertRow) => a.status === "pending_review");
  const photos = images.filter((im) => im.image_id && isRealNewsThumb(im));
  const entityKinds = (["DISEASE", "ANIMAL", "COUNTRY", "ORG"] as const).filter(
    (kindKey) => (grouped[kindKey] || []).length,
  );
  const articleThumb = article ? thumbSrc(article) : null;
  const heroSrc =
    article?.is_news_thumb === false
      ? youtubeThumbUrl(article?.url)
      : articleThumb || (photos[0] ? imageSrc(photos[0]) : youtubeThumbUrl(article?.url));
  const galleryPhotos = photos.filter((im, idx) => {
    const src = imageSrc(im);
    if (heroSrc && src === heroSrc) return false;
    if (idx === 0 && heroSrc && article?.is_news_thumb !== false) return false;
    return true;
  });
  const kind = article ? sourceKind(article) : "prensa";
  const sourceName = article ? displaySourceName(article, source?.name) : "Fuente";
  const when = formatDate(article?.published_at || article?.collected_at);
  const hideMap = !geo || geo.country === "XX" || geo.country === "INT" || geo.lat == null;
  const clip = photos.find((im) => im.encoder) || photos[0];

  const officialSources = useMemo(() => uniqueOfficialSources(evidence), [evidence]);
  const titleText = article?.title || "";
  const summaryText = flowText(article?.text || article?.summary);
  const lecturaText = flowText(article?.local_explanation || article?.llm_explanation);
  const [tTitle, tSummary, tLectura] = useTranslated([titleText, summaryText, lecturaText]);

  async function review(label: "validado" | "descartado" | "modificado") {
    const alert = alerts[0];
    if (!alert) return;
    if (label === "modificado" && !modReason.trim()) {
      setModOpen(true);
      return;
    }
    setHitlBusy(true);
    try {
      await api.review(alert.alert_id, label, modReason);
      setHitlNote(`Revisión: ${label}`);
      setModOpen(false);
      await reload();
    } catch {
      setHitlNote("No se pudo guardar la revisión.");
    } finally {
      setHitlBusy(false);
    }
  }

  return (
    <div className="shell analysis">
      <AppHeader
        title={tTitle || article?.title || (err ? "Artículo no encontrado" : "Cargando ficha…")}
        subtitle={article ? `${sourceName} · ${when}` : undefined}
      />
      {err && (
        <section className="viz">
          <p className="banner err">{err}</p>
          <p className="muted">
            No se encontró este artículo. Estos son algunos recientes:
          </p>
          <LeerMas maxItems={3} as="ul" className="similar-list">
            {recent.map((a) => (
              <li key={a.content_id}>
                <Link to={articleHref(a.content_id)}>{a.title || a.content_id}</Link>
              </li>
            ))}
          </LeerMas>
        </section>
      )}
      {!article && !err && <p className="muted">Cargando ficha…</p>}
      {article && (
        <div className="analysis-body" key={article.content_id}>
          <div className="analysis-col decision">
            <section className="viz">
              <div className="art-pills">
                <span className={`type-chip kind-${kind}`}>{KIND_LABEL[kind]}</span>
                <span className={`pill ${verdictClass(article.verdict)}`}>{verdictLabel(article.verdict)}</span>
                <span className={`pill risk-pill ${riskTone(article.risk_score)}`}>
                  {article.risk_score == null ? "Riesgo —" : `Riesgo ${article.risk_score}`}
                </span>
              </div>
              <p className="meta">
                {sourceName} · {when} · {geo?.name || article.country || "Sin país"}
              </p>
              {clip?.encoder ? (
                <p className="clip-line">
                  {clip.encoder} · {clip.visual_fusion?.type || clip.cnn_class || "—"}
                  {clip.cnn_confidence != null ? ` ${Number(clip.cnn_confidence).toFixed(2)}` : ""}
                  {clip.ocr_text ? ` · OCR: ${clip.ocr_text.slice(0, 80)}` : ""}
                </p>
              ) : null}
              {alerts.length ? (
                <div className="hitl-ficha">
                  <p className="muted">Alerta pendiente de revisión humana</p>
                  {hitlNote ? <p className="banner">{hitlNote}</p> : null}
                  <HitlButtons busy={hitlBusy} onAct={review} />
                  {modOpen ? (
                    <label className="hitl-reason">
                      Motivo (obligatorio)
                      <textarea value={modReason} onChange={(e) => setModReason(e.target.value)} rows={3} />
                      <button type="button" className="run" disabled={!modReason.trim() || hitlBusy} onClick={() => review("modificado")}>
                        Guardar modificación
                      </button>
                    </label>
                  ) : null}
                </div>
              ) : null}
            </section>

            <section className={`viz claims-block${!claims.length && !officialSources.length ? " is-empty" : ""}`}>
              <h3>Afirmaciones y evidencia</h3>
              {claims.length ? (
                <LeerMas maxItems={3} as="ul" className="claim-list">
                  {claims.map((claim) => {
                    const open = openClaimId === claim.claim_id;
                    return (
                      <li key={claim.claim_id} className={`claim-item${open ? " is-open" : ""}`}>
                        <button
                          type="button"
                          className="claim-compact"
                          aria-expanded={open}
                          onClick={() => setOpenClaimId(open ? null : claim.claim_id)}
                        >
                          <span className={`pill ${verdictClass(claim.nli_label)}`}>{stanceLabel(claim.nli_label)}</span>
                          <span className="claim-compact-text">{flowText(claim.text)}</span>
                        </button>
                        {open ? <p className="claim-expanded">{flowText(claim.text)}</p> : null}
                      </li>
                    );
                  })}
                </LeerMas>
              ) : (
                <p className="muted">No se encontraron afirmaciones (el texto era corto o no había frases claras).</p>
              )}
              <div className={`fuentes-oficiales${officialSources.length ? "" : " is-empty"}`}>
                <h4>Fuentes oficiales</h4>
                {officialSources.length ? (
                  <ul className="fuentes-list">
                    {officialSources.map((e) => (
                      <li key={e.evidence_id} className="fuente-item">
                        <span className="fuente-host">{officialLabel(e.url)}</span>
                        {isAllowlistedHttp(e.url) ? (
                          <a className="ext" href={e.url!} target="_blank" rel="noopener noreferrer">
                            {e.url}
                          </a>
                        ) : (
                          <span className="muted">Sin enlace público</span>
                        )}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="muted">Sin evidencia oficial disponible</p>
                )}
              </div>
            </section>

            <div className="analysis-below-pair">
              <section className={`viz compact${timeline.length ? "" : " is-empty"}`}>
                <h3>Línea de tiempo</h3>
                {timeline.length ? (
                  <ol className="timeline compact">
                    {timeline.map((t: any, i: number) => (
                      <li key={i} className={t.kind}>
                        <span>{t.label}</span>
                        <strong>{formatDate(t.at)}</strong>
                        {t.text ? <p>{flowText(t.text)}</p> : null}
                      </li>
                    ))}
                  </ol>
                ) : (
                  <p className="muted">Sin fechas registradas.</p>
                )}
              </section>

              <section className={`viz compact${entityKinds.length ? "" : " is-empty"}`}>
                <h3>Entidades</h3>
                {entityKinds.length ? (
                  <div className="entity-groups dense">
                    {entityKinds.map((kindKey) => (
                      <div key={kindKey}>
                        <h4>{entityKindLabel(kindKey)}</h4>
                        <div className="chips">
                          {(grouped[kindKey] || []).map((v) => (
                            <span key={v} className="chip">
                              {v}
                            </span>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="muted">Sin entidades extraídas.</p>
                )}
              </section>
            </div>

            <section className={`viz compact analysis-similar${similar.length ? "" : " is-empty"}`}>
              <h3>Artículos similares</h3>
              {similar.length ? (
                <LeerMas maxItems={4} as="ul" className="similar-list">
                  {similar.map((s: { content_id: string; title: string; score?: number; reasons?: string[] }) => (
                    <li key={s.content_id}>
                      <Link to={articleHref(s.content_id)}>{s.title || s.content_id}</Link>
                      {s.reasons?.length ? <span className="muted"> · {s.reasons.join(", ")}</span> : null}
                    </li>
                  ))}
                </LeerMas>
              ) : (
                <p className="muted">Sin pares similares todavía.</p>
              )}
            </section>
          </div>

          <div className="analysis-col context">
            <section className="viz">
              {heroSrc ? (
                <div className="hero-photo">
                  <SafeImg src={heroSrc} alt="" />
                </div>
              ) : null}
              <LeerMas maxLines={4} className="lede">
                {tSummary || "Sin texto en el cuerpo."}
              </LeerMas>
              {isAllowlistedHttp(article.url) ? (
                <p>
                  <a className="ext" href={article.url} target="_blank" rel="noopener noreferrer">
                    Abrir fuente original
                  </a>
                </p>
              ) : null}
            </section>

            <section className="viz llm-compact">
              <h3>Lectura del caso</h3>
              <div className={`quality ${quality?.band || "media"}`}>
                {quality?.llm_used ? "Hay explicación automática" : "Lectura a partir del texto"}
                {claims.length ? ` · ${claims.length} afirmaciones` : " · sin afirmaciones"}
              </div>
              <LeerMas maxLines={4}>
                {tLectura || "Sin lectura del caso."}
              </LeerMas>
            </section>

            {!hideMap ? (
              <section className="viz">
                <h3>Ubicación</h3>
                <MapView points={[geo]} height={280} focus={{ lat: geo.lat!, lng: geo.lng!, label: geo.name }} />
              </section>
            ) : null}
          </div>

          {galleryPhotos.length ? (
            <section className="viz compact analysis-images">
              <h3>Imágenes</h3>
              <div className="img-gallery">
                {galleryPhotos.map((im) => (
                  <div key={im.image_id} className="gallery-item">
                    <SafeImg src={imageSrc(im)} alt={im.cnn_class || "imagen del caso"} />
                    <div>
                      {im.encoder ? (
                        <p className="clip-line">
                          {im.encoder} · {im.visual_fusion?.type || im.cnn_class || "—"}
                          {im.cnn_confidence != null ? ` ${Number(im.cnn_confidence).toFixed(2)}` : ""}
                        </p>
                      ) : null}
                      <details>
                        <summary>CNN académica</summary>
                        <strong className="cnn-class">{im.cnn_class || "SIN_CLASE"}</strong>
                        <SoftmaxBars scores={im.cnn_scores} />
                      </details>
                      {im.ocr_text?.trim() ? (
                        <LeerMas maxLines={3} className="ocr-box">
                          {flowText(im.ocr_text)}
                        </LeerMas>
                      ) : (
                        <div className="ocr-box ocr-empty">Sin texto en la imagen</div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </section>
          ) : null}
        </div>
      )}
    </div>
  );
}
