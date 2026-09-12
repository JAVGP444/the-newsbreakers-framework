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
} from "./api";
import AppHeader from "./components/AppHeader";
import { SoftmaxBars } from "./components/ImageCard";
import LeerMas from "./components/LeerMas";
import MapView from "./components/MapView";
import { HitlButtons } from "./Observatory";
import SafeImg from "./components/SafeImg";
import {
  KIND_LABEL,
  articleLede,
  displayClaim,
  displaySourceName,
  entityKindLabel,
  flowText,
  formatDate,
  formatPublishedAt,
  isRealNewsThumb,
  riskHeadline,
  riskTone,
  sourceKind,
  youtubeThumbUrl,
  stanceLabel,
  verdictLabel,
  cnnConfidenceWhy,
} from "./display";
import { hydratePoint } from "./geoCentroids";
import { isSafeExternalHttp, articleHref } from "./safeUrl";
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

function claimWhyShort(claim: Claim): string {
  const expl = claim.nli_explain;
  const stance = stanceLabel(expl?.label || claim.nli_label);
  const official = (expl?.items || []).find((item) => item.official) || expl?.items?.[0];
  if (!official) {
    return stance === "Sin verificar" ? "No hay ficha oficial contra la que cruzar esta frase." : "";
  }
  const name = officialLabel(official.url);
  const miss = (official.missing || [])[0];
  if (stance === "Respaldado") return `Coincide con la ficha de ${name}.`;
  if (stance === "Contradicho") {
    return miss ? `Choca con ${name}: ${miss}` : `Choca con la ficha de ${name}.`;
  }
  return miss ? `${name}: ${miss}` : `No alcanza para respaldar con ${name}.`;
}

function isTemplateLectura(text?: string | null): boolean {
  const t = (text || "").trim();
  if (!t) return true;
  return /^lectura del caso/i.test(t) || /p[aá]rrafo se arma/i.test(t);
}

function RiskBrief({ why, score }: { why?: import("./api").Article["risk_why"]; score?: number | null }) {
  const rows = why?.explain?.rows || [];
  const line = riskHeadline(why, score);
  if (!line && !rows.length) return null;
  return (
    <div className="risk-brief">
      {line ? <p className="ficha-lead">{line}</p> : null}
      {why?.numeric?.reason && why.numeric.claim != null && why.numeric.official != null ? (
        <p className="muted">
          Cifra en la nota: {why.numeric.claim}. Parte oficial: {why.numeric.official}.
        </p>
      ) : null}
      {rows.length ? (
        <details className="calc-fold">
          <summary>Cómo se calculó el riesgo</summary>
          <ul className="risk-parts">
            {rows.map((row) => (
              <li key={row.id}>
                <span>{row.label}</span>
                <span className="risk-part-bar">
                  <i style={{ width: `${Math.max(0, Math.min(100, Number(row.value) || 0))}%` }} />
                </span>
                <strong>{row.contrib}</strong>
              </li>
            ))}
          </ul>
          {rows.map((row) => (
            <p key={`${row.id}-why`} className="param-why">
              <strong>{row.label}.</strong> {row.why}
            </p>
          ))}
        </details>
      ) : null}
    </div>
  );
}

function ClaimDetail({ claim, title }: { claim: Claim; title?: string }) {
  const expl = claim.nli_explain;
  const why = claimWhyShort(claim);
  const items = expl?.items || [];
  return (
    <div className="claim-expanded">
      <p>{displayClaim(claim.text, title)}</p>
      {why ? <p className="ficha-lead">{why}</p> : null}
      {items.length ? (
        <details className="calc-fold">
          <summary>Cruce con fichas oficiales</summary>
          <ul className="nli-plain">
            {items.map((item, i) => (
              <li key={item.url || String(i)}>
                <strong>{officialLabel(item.url)}</strong>
                {item.missing?.length ? `: ${item.missing[0]}` : item.official ? " · ficha oficial" : ""}
              </li>
            ))}
          </ul>
        </details>
      ) : null}
    </div>
  );
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
  const when = formatPublishedAt(article?.published_at);
  const hideMap = !geo || geo.country === "XX" || geo.country === "INT" || geo.lat == null;

  const officialSources = useMemo(() => uniqueOfficialSources(evidence), [evidence]);
  const titleText = article?.title || "";
  const summaryText = articleLede(article?.text || article?.summary, article?.title);
  const rawLectura = flowText(article?.local_explanation || article?.llm_explanation);
  const lecturaText = isTemplateLectura(rawLectura) ? "" : rawLectura;
  const [tTitle, tSummary, tLectura] = useTranslated([titleText, summaryText, lecturaText]);

  async function review(label: "validado" | "descartado" | "modificado") {
    if (!article?.content_id) return;
    if (label === "modificado" && !modReason.trim()) {
      setModOpen(true);
      return;
    }
    setHitlBusy(true);
    try {
      const body = await api.reviewArticle(article.content_id, label, modReason);
      const next = body.article?.verdict || "";
      setHitlNote(next ? `Revisión guardada (${label}). Veredicto: ${next}` : `Revisión guardada: ${label}`);
      setModOpen(false);
      await reload();
    } catch (e) {
      setHitlNote(e instanceof Error ? e.message : "No se pudo guardar la revisión.");
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
          <p className="muted">No se encontró este artículo. Estos son algunos recientes:</p>
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
          <div className="analysis-col context">
            <section className="viz story">
              {heroSrc ? (
                <div className="hero-photo">
                  <SafeImg src={heroSrc} alt="" />
                </div>
              ) : null}
              <p className="meta">
                {sourceName} · {when} · {geo?.name || article.country || "Sin país"}
              </p>
              {tSummary ? (
                <LeerMas maxLines={5} className="lede">
                  {tSummary}
                </LeerMas>
              ) : (
                <p className="lede-empty">Esta nota no trajo cuerpo. Abre el original.</p>
              )}
              {isSafeExternalHttp(article.url) ? (
                <p>
                  <a className="ext" href={article.url} target="_blank" rel="noopener noreferrer">
                    Abrir noticia original
                  </a>
                </p>
              ) : null}
            </section>

            {entityKinds.length || tLectura ? (
              <section className="viz">
                <h3>El caso</h3>
                {entityKinds.length ? (
                  <dl className="case-facts">
                    {entityKinds.map((kindKey) => (
                      <div key={kindKey}>
                        <dt>{entityKindLabel(kindKey)}</dt>
                        <dd>{(grouped[kindKey] || []).slice(0, 4).join(", ")}</dd>
                      </div>
                    ))}
                  </dl>
                ) : null}
                {tLectura ? (
                  <LeerMas maxLines={4} className="lectura-extra">
                    {tLectura}
                  </LeerMas>
                ) : null}
              </section>
            ) : null}

            {!hideMap ? (
              <section className="viz">
                <h3>Ubicación</h3>
                <MapView points={[geo]} height={240} focus={{ lat: geo.lat!, lng: geo.lng!, label: geo.name }} />
              </section>
            ) : null}

            {timeline.length ? (
              <section className="viz compact">
                <h3>Línea de tiempo</h3>
                <ol className="timeline compact">
                  {timeline.map((t: { kind?: string; label?: string; at?: string; text?: string }, i: number) => (
                    <li key={i} className={t.kind}>
                      <span>{t.label}</span>
                      <strong>{formatDate(t.at)}</strong>
                      {t.text && flowText(t.text) !== flowText(article.title) ? <p>{flowText(t.text)}</p> : null}
                    </li>
                  ))}
                </ol>
              </section>
            ) : null}
          </div>

          <div className="analysis-col decision">
            <section className="viz">
              <div className="art-pills wrap">
                <span className={`type-chip kind-${kind}`}>{KIND_LABEL[kind]}</span>
                <span className={`pill ${verdictClass(article.verdict)}`}>{verdictLabel(article.verdict)}</span>
                <span className={`pill risk-pill ${riskTone(article.risk_score)}`}>
                  {article.risk_score == null ? "Riesgo —" : `Riesgo ${article.risk_score}/100`}
                </span>
              </div>
              <RiskBrief why={article.risk_why} score={article.risk_score} />
              <div className="hitl-ficha">
                <p className="muted">{alerts.length ? "Alerta pendiente de revisión humana" : "Revisión humana"}</p>
                {hitlNote ? <p className="banner">{hitlNote}</p> : null}
                <HitlButtons busy={hitlBusy} onAct={review} />
                {modOpen ? (
                  <label className="hitl-reason">
                    Motivo (obligatorio)
                    <textarea value={modReason} onChange={(e) => setModReason(e.target.value)} rows={3} />
                    <button
                      type="button"
                      className="run"
                      disabled={!modReason.trim() || hitlBusy}
                      onClick={() => review("modificado")}
                    >
                      Guardar modificación
                    </button>
                  </label>
                ) : null}
              </div>
            </section>

            <section className={`viz claims-block${!claims.length && !officialSources.length ? " is-empty" : ""}`}>
              <h3>Afirmaciones</h3>
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
                          <span className="claim-compact-text">{displayClaim(claim.text, article.title)}</span>
                        </button>
                        {open ? <ClaimDetail claim={claim} title={article.title} /> : null}
                      </li>
                    );
                  })}
                </LeerMas>
              ) : (
                <p className="muted">No hay frases claras que cruzar con las fichas.</p>
              )}
              <div className={`fuentes-oficiales${officialSources.length ? "" : " is-empty"}`}>
                <h4>Fuentes oficiales</h4>
                {officialSources.length ? (
                  <ul className="fuente-chips">
                    {officialSources.map((e) => (
                      <li key={e.evidence_id}>
                        {isSafeExternalHttp(e.url) ? (
                          <a href={e.url!} target="_blank" rel="noopener noreferrer">
                            {officialLabel(e.url)}
                          </a>
                        ) : (
                          <span>{officialLabel(e.url)}</span>
                        )}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="muted">Sin evidencia oficial disponible</p>
                )}
              </div>
            </section>
          </div>

          {similar.length ? (
            <section className="viz compact analysis-similar">
              <h3>Artículos similares</h3>
              <LeerMas maxItems={4} as="ul" className="similar-list">
                {similar.map((s: { content_id: string; title: string; score?: number; reasons?: string[] }) => (
                  <li key={s.content_id}>
                    <Link to={articleHref(s.content_id)}>{s.title || s.content_id}</Link>
                    {s.reasons?.length ? <span className="muted"> · {s.reasons.join(", ")}</span> : null}
                  </li>
                ))}
              </LeerMas>
            </section>
          ) : null}

          {galleryPhotos.length ? (
            <section className="viz compact analysis-images">
              <h3>Imágenes</h3>
              <div className="img-gallery">
                {galleryPhotos.map((im) => (
                  <div key={im.image_id} className="gallery-item">
                    <SafeImg src={imageSrc(im)} alt={im.cnn_class || "imagen del caso"} />
                    <div>
                      {im.cnn_confidence != null || im.cnn_class ? (
                        <p className="clip-line">
                          {im.visual_fusion?.type || im.cnn_class || "—"}
                          {im.cnn_confidence != null ? ` · ${Math.round(Number(im.cnn_confidence) * 100)}%` : ""}
                        </p>
                      ) : null}
                      <details>
                        <summary>Tipo de imagen</summary>
                        {cnnConfidenceWhy(im) ? <p className="muted cnn-why">{cnnConfidenceWhy(im)}</p> : null}
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
