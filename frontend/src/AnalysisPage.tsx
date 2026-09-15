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
  type NarrativeAnalysis,
} from "./api";
import AppHeader from "./components/AppHeader";
import { SoftmaxBars } from "./components/ImageCard";
import LeerMas from "./components/LeerMas";
import MapView from "./components/MapView";
import { HitlButtons } from "./Observatory";
import SafeImg from "./components/SafeImg";
import {
  articleLede,
  displayClaim,
  displaySourceName,
  entityKindLabel,
  flowText,
  formatDate,
  formatPublishedAt,
  isRealNewsThumb,
  kindLabel,
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
import { useLocale } from "./locale";
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

function claimWhyShort(claim: Claim, lang: "es" | "en", t: (k: string, v?: Record<string, string | number>) => string): string {
  const expl = claim.nli_explain;
  const stance = stanceLabel(expl?.label || claim.nli_label, lang);
  const official = (expl?.items || []).find((item) => item.official) || expl?.items?.[0];
  if (!official) {
    return stance === t("verdict.sin") ? t("analysis.whyNone") : "";
  }
  const name = officialLabel(official.url);
  const miss = (official.missing || [])[0];
  if (stance === t("verdict.respaldado")) return t("analysis.whyMatch", { name });
  if (stance === t("verdict.contradicho")) {
    return miss ? t("analysis.whyClashMiss", { name, miss }) : t("analysis.whyClash", { name });
  }
  return miss ? t("analysis.whyShort", { name, miss }) : t("analysis.whyWeak", { name });
}

function isTemplateLectura(text?: string | null): boolean {
  const t = (text || "").trim();
  if (!t) return true;
  return /^lectura del caso/i.test(t) || /p[aá]rrafo se arma/i.test(t);
}

function RiskBrief({ why, score }: { why?: import("./api").Article["risk_why"]; score?: number | null }) {
  const { t } = useLocale();
  const rows = why?.explain?.rows || [];
  const line = riskHeadline(why, score);
  if (!line && !rows.length) return null;
  return (
    <div className="risk-brief">
      {line ? <p className="ficha-lead">{line}</p> : null}
      {why?.numeric?.reason && why.numeric.claim != null && why.numeric.official != null ? (
        <p className="muted">
          {t("analysis.figure", { claim: why.numeric.claim, official: why.numeric.official })}
        </p>
      ) : null}
      {rows.length ? (
        <details className="calc-fold">
          <summary>{t("article.riskHow")}</summary>
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
  const { t, lang } = useLocale();
  const expl = claim.nli_explain;
  const why = claimWhyShort(claim, lang, t);
  const items = expl?.items || [];
  return (
    <div className="claim-expanded">
      <p>{displayClaim(claim.text, title)}</p>
      {why ? <p className="ficha-lead">{why}</p> : null}
      {items.length ? (
        <details className="calc-fold">
          <summary>{t("analysis.nli")}</summary>
          <ul className="nli-plain">
            {items.map((item, i) => (
              <li key={item.url || String(i)}>
                <strong>{officialLabel(item.url)}</strong>
                {item.missing?.length ? `: ${item.missing[0]}` : item.official ? t("analysis.officialCard") : ""}
              </li>
            ))}
          </ul>
        </details>
      ) : null}
    </div>
  );
}

function ContrastNarrative({ narrative }: { narrative: NarrativeAnalysis }) {
  const { t } = useLocale();
  const card = narrative.contrast;
  const cls = narrative.classification || card?.conclusion;
  return (
    <section className="viz contrast-block">
      <h3>{t("analysis.contrast")}</h3>
      <p className="muted">{narrative.principle}</p>
      {cls ? (
        <p className="ficha-lead">
          <span className={`pill nar-${cls.code}`}>{cls.label}</span> {cls.why}
        </p>
      ) : null}
      {card ? (
        <dl className="case-facts contrast-facts">
          <div>
            <dt>{t("analysis.claim")}</dt>
            <dd>{card.afirmacion}</dd>
          </div>
          <div>
            <dt>{t("analysis.noteEv")}</dt>
            <dd>{card.evidencia_afirmacion}</dd>
          </div>
          <div>
            <dt>{t("analysis.official")}</dt>
            <dd>
              {card.informacion_oficial?.length
                ? card.informacion_oficial.map((o) => o.host || o.title).join(" · ")
                : t("analysis.noOfficial")}
            </dd>
          </div>
          {card.normativa ? (
            <div>
              <dt>{t("analysis.norm")}</dt>
              <dd>{card.normativa}</dd>
            </div>
          ) : null}
          <div>
            <dt>{t("analysis.unproven")}</dt>
            <dd>
              {card.no_comprobado?.length
                ? card.no_comprobado.map((c) => c.text).filter(Boolean).join(" · ")
                : t("analysis.nothing")}
            </dd>
          </div>
        </dl>
      ) : null}
      {narrative.signals?.length ? (
        <LeerMas maxItems={4} as="ul" className="signal-list">
          {narrative.signals.map((s, i) => (
            <li key={`${s.modality}-${i}`}>
              <span className="pill mid">{s.modality_label}</span>
              <span>
                {s.hits.map((h) => h.term).join(", ")}. {s.note}
              </span>
            </li>
          ))}
        </LeerMas>
      ) : (
        <p className="muted">{t("analysis.noSignals")}</p>
      )}
      {narrative.claims?.length > 1 ? (
        <div>
          <h4>{t("analysis.split")}</h4>
          <ol className="split-claims">
            {narrative.claims.slice(0, 6).map((c, i) => (
              <li key={i}>{c.text}</li>
            ))}
          </ol>
        </div>
      ) : null}
    </section>
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
  const { t, lang } = useLocale();
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
          setErr(t("article.notFound"));
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
  const when = formatPublishedAt(article?.published_at, lang);
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
      setHitlNote(next ? `Revisión guardada (${label}). Veredicto: ${next}` : t("nar.saved", { label }));
      setModOpen(false);
      await reload();
    } catch (e) {
      setHitlNote(e instanceof Error ? e.message : t("common.saveFail"));
    } finally {
      setHitlBusy(false);
    }
  }

  return (
    <div className="shell analysis">
      <AppHeader
        title={tTitle || article?.title || (err ? t("article.missing") : t("article.loading"))}
        subtitle={article ? `${sourceName} · ${when}` : undefined}
      />
      {err && (
        <section className="viz">
          <p className="banner err">{err}</p>
          <p className="muted">{t("article.missingList")}</p>
          <LeerMas maxItems={3} as="ul" className="similar-list">
            {recent.map((a) => (
              <li key={a.content_id}>
                <Link to={articleHref(a.content_id)}>{a.title || a.content_id}</Link>
              </li>
            ))}
          </LeerMas>
        </section>
      )}
      {!article && !err && <p className="muted">{t("article.loading")}</p>}
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
                {sourceName} · {when} · {geo?.name || article.country || t("common.noCountry")}
              </p>
              {tSummary ? (
                <LeerMas maxLines={5} className="lede">
                  {tSummary}
                </LeerMas>
              ) : (
                <p className="lede-empty">{t("article.noBody")}</p>
              )}
              {isSafeExternalHttp(article.url) ? (
                <p>
                  <a className="ext" href={article.url} target="_blank" rel="noopener noreferrer">
                    {t("article.openOriginal")}
                  </a>
                </p>
              ) : null}
            </section>

            {entityKinds.length || tLectura ? (
              <section className="viz">
                <h3>{t("article.case")}</h3>
                {entityKinds.length ? (
                  <dl className="case-facts">
                    {entityKinds.map((kindKey) => (
                      <div key={kindKey}>
                        <dt>{entityKindLabel(kindKey, lang)}</dt>
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
                <h3>{t("article.place")}</h3>
                <MapView points={[geo]} height={240} focus={{ lat: geo.lat!, lng: geo.lng!, label: geo.name }} />
              </section>
            ) : null}

            {timeline.length ? (
              <section className="viz compact">
                <h3>{t("article.timeline")}</h3>
                <ol className="timeline compact">
                  {timeline.map((t: { kind?: string; label?: string; at?: string; text?: string }, i: number) => (
                    <li key={i} className={t.kind}>
                      <span>{t.label}</span>
                      <strong>{formatDate(t.at, lang)}</strong>
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
                <span className={`type-chip kind-${kind}`}>{kindLabel(kind, lang)}</span>
                <span className={`pill ${verdictClass(article.verdict)}`}>{verdictLabel(article.verdict, lang)}</span>
                {data.narrative?.classification ? (
                  <span className={`pill nar-${data.narrative.classification.code}`}>
                    {data.narrative.classification.label}
                  </span>
                ) : null}
                <span className={`pill risk-pill ${riskTone(article.risk_score)}`}>
                  {article.risk_score == null ? t("risk.dash") : t("risk.of", { n: article.risk_score })}
                </span>
              </div>
              <RiskBrief why={article.risk_why} score={article.risk_score} />
              <div className="hitl-ficha">
                <p className="muted">{alerts.length ? t("article.alertPending") : t("article.human")}</p>
                {hitlNote ? <p className="banner">{hitlNote}</p> : null}
                <HitlButtons busy={hitlBusy} onAct={review} />
                {modOpen ? (
                  <label className="hitl-reason">
                    {t("article.reason")}
                    <textarea value={modReason} onChange={(e) => setModReason(e.target.value)} rows={3} />
                    <button
                      type="button"
                      className="run"
                      disabled={!modReason.trim() || hitlBusy}
                      onClick={() => review("modificado")}
                    >
                      {t("article.saveMod")}
                    </button>
                  </label>
                ) : null}
              </div>
            </section>

            <section className={`viz claims-block${!claims.length && !officialSources.length ? " is-empty" : ""}`}>
              <h3>{t("article.claims")}</h3>
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
                          <span className={`pill ${verdictClass(claim.nli_label)}`}>{stanceLabel(claim.nli_label, lang)}</span>
                          <span className="claim-compact-text">{displayClaim(claim.text, article.title)}</span>
                        </button>
                        {open ? <ClaimDetail claim={claim} title={article.title} /> : null}
                      </li>
                    );
                  })}
                </LeerMas>
              ) : (
                <p className="muted">{t("article.noClaims")}</p>
              )}
              <div className={`fuentes-oficiales${officialSources.length ? "" : " is-empty"}`}>
                <h4>{t("article.official")}</h4>
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
                  <p className="muted">{t("article.noOfficial")}</p>
                )}
              </div>
            </section>
            {data.narrative ? <ContrastNarrative narrative={data.narrative} /> : null}
          </div>

          {similar.length ? (
            <section className="viz compact analysis-similar">
              <h3>{t("article.similar")}</h3>
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
              <h3>{t("article.images")}</h3>
              <div className="img-gallery">
                {galleryPhotos.map((im) => (
                  <div key={im.image_id} className="gallery-item">
                    <SafeImg src={imageSrc(im)} alt={im.cnn_class || t("image.alt")} />
                    <div>
                      {im.cnn_confidence != null || im.cnn_class ? (
                        <p className="clip-line">
                          {im.visual_fusion?.type || im.cnn_class || "—"}
                          {im.cnn_confidence != null ? ` · ${Math.round(Number(im.cnn_confidence) * 100)}%` : ""}
                        </p>
                      ) : null}
                      <details>
                        <summary>{t("article.imageType")}</summary>
                        {cnnConfidenceWhy(im) ? <p className="muted cnn-why">{cnnConfidenceWhy(im)}</p> : null}
                        <strong className="cnn-class">{im.cnn_class || "SIN_CLASE"}</strong>
                        <SoftmaxBars scores={im.cnn_scores} />
                      </details>
                      {im.ocr_text?.trim() ? (
                        <LeerMas maxLines={3} className="ocr-box">
                          {flowText(im.ocr_text)}
                        </LeerMas>
                      ) : (
                        <div className="ocr-box ocr-empty">{t("article.noOcr")}</div>
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
