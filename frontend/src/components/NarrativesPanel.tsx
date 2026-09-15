import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type NarrativeDossier, type NarrativeOverview } from "../api";
import { useLocale } from "../locale";
import NarrativeCharts from "./NarrativeCharts";
import NetworkGraph from "./NetworkGraph";
import { MiniBars } from "./Sparkline";

export type NarrativeSurface = "sala" | "revision" | "graficas" | "grafo";

export default function NarrativesPanel({ query, surface = "sala" }: { query: string; surface?: NarrativeSurface }) {
  const { t } = useLocale();
  const forceOpts = [
    { id: "1", label: t("nar.force1") },
    { id: "3", label: t("nar.force3") },
    { id: "4", label: t("nar.force4") },
  ];
  const [data, setData] = useState<NarrativeOverview | null>(null);
  const [err, setErr] = useState("");
  const [category, setCategory] = useState("");
  const [forceMin, setForceMin] = useState("1");
  const [selected, setSelected] = useState<string>("");
  const [note, setNote] = useState("");

  useEffect(() => {
    let cancelled = false;
    const params = new URLSearchParams(query);
    if (category) params.set("category", category);
    params.set("force_min", forceMin);
    api
      .narrativesOverview(params.toString())
      .then((row) => {
        if (cancelled) return;
        setData(row);
        setErr("");
        const first = row.narratives?.[0]?.narrative_id;
        setSelected((cur) => cur || first || "");
      })
      .catch(() => {
        if (!cancelled) setErr(t("nar.loadFail"));
      });
    return () => {
      cancelled = true;
    };
  }, [query, category, forceMin]);

  const dossier = (data?.narratives || []).find((n) => n.narrative_id === selected) || data?.narratives?.[0] || null;

  async function review(label: string) {
    if (!dossier) return;
    try {
      await api.reviewNarrative(dossier.narrative_id, label, "Revisión desde narrativas");
      setNote(t("nar.saved", { label }));
    } catch (e) {
      setNote(e instanceof Error ? e.message : t("nar.saveFail"));
    }
  }

  if (err) return <p className="banner err">{err}</p>;
  if (!data) return <p className="muted">{t("nar.loading")}</p>;

  const onSala = surface === "sala";
  const onRevision = surface === "revision";
  const onGraficas = surface === "graficas";
  const onGrafo = surface === "grafo";

  return (
    <div className="narrative-stack">
      {onSala || onRevision ? (
        <p className="muted">
          {data.principle} {t("nar.cut", { n: data.sample, available: data.sources_available ?? "—", used: data.sources_used ?? "—" })}
        </p>
      ) : null}

      {onSala && data.kpis ? (
        <section className="kpis" aria-label={t("nar.kpis")}>
          <div className="kpi">
            <span>{t("nar.stories")}</span>
            <strong>{data.kpis.narratives ?? 0}</strong>
          </div>
          <div className="kpi">
            <span>{t("nar.growing")}</span>
            <strong>{data.kpis.growing ?? 0}</strong>
          </div>
          <div className="kpi">
            <span>{t("nar.priority")}</span>
            <strong>{data.kpis.priority ?? 0}</strong>
          </div>
          <div className="kpi">
            <span>{t("nar.claims")}</span>
            <strong>{data.kpis.claims ?? 0}</strong>
          </div>
        </section>
      ) : null}

      {onRevision && (data.alerts || []).length ? (
        <section className="viz">
          <h3>{t("nar.alerts")}</h3>
          <p className="muted">{t("nar.alertsLead")}</p>
          <ul className="method-list">
            {data.alerts?.map((a) => (
              <li key={a.narrative_id}>
                <button type="button" className="chip" onClick={() => setSelected(a.narrative_id)}>
                  {a.label}
                </button>{" "}
                {a.growth_pct ? `+${a.growth_pct}% · ` : ""}
                {a.reason}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {onSala ? (
      <section className="viz">
        <h3>{t("nar.grouped")}</h3>
        <p className="muted">{t("nar.groupedLead")}</p>
        {(data.narratives || []).length ? (
          <div className="source-table-wrap">
            <table className="source-table">
              <thead>
                <tr>
                  <th>{t("nar.col.story")}</th>
                  <th>{t("nar.col.state")}</th>
                  <th>{t("nar.col.notes")}</th>
                  <th>{t("nar.col.growth")}</th>
                  <th>{t("nar.col.priority")}</th>
                  <th>{t("nar.col.contrast")}</th>
                </tr>
              </thead>
              <tbody>
                {(data.narratives || []).map((n) => (
                  <tr
                    key={n.narrative_id}
                    className={n.narrative_id === dossier?.narrative_id ? "row-on" : ""}
                    onClick={() => setSelected(n.narrative_id)}
                  >
                    <td>
                      <strong>{n.label}</strong>
                      <div className="muted">{n.description}</div>
                    </td>
                    <td>{n.state_label || n.state || "—"}</td>
                    <td>{n.volume}</td>
                    <td>{n.growth_pct != null ? `${n.growth_pct}%` : "—"}</td>
                    <td>{n.priority?.label || "—"}</td>
                    <td>
                      {n.contrast_level ? `N${n.contrast_level.level} · ${n.contrast_level.label}` : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="muted">{t("nar.empty")}</p>
        )}
      </section>
      ) : null}

      {(onSala || onRevision) && dossier ? <Dossier n={dossier} onReview={review} note={note} compact={onSala} /> : null}

      {onGrafo ? (
      <section className="viz">
        <h3>{t("nar.concepts")}</h3>
        <div className="filter-row">
          <label>
            {t("nar.category")}
            <select value={category} onChange={(e) => setCategory(e.target.value)}>
              <option value="">{t("filter.all")}</option>
              {(data.categories || []).map((c) => (
                <option key={c.id} value={c.id}>
                  {c.label} ({c.count})
                </option>
              ))}
            </select>
          </label>
          <label>
            {t("nar.force")}
            <select value={forceMin} onChange={(e) => setForceMin(e.target.value)}>
              {forceOpts.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.label}
                </option>
              ))}
            </select>
          </label>
        </div>
        {data.graph?.nodes?.length ? (
          <NetworkGraph nodes={data.graph.nodes} edges={data.graph.edges} height={420} />
        ) : (
          <p className="muted">{t("nar.noCo")}</p>
        )}
      </section>
      ) : null}

      {onGraficas ? <NarrativeCharts data={data} /> : null}

      {onGrafo ? (
      <section className="viz">
        <h3>{t("nar.rels")}</h3>
        {data.pairs.length ? (
          <div className="source-table-wrap">
            <table className="source-table">
              <thead>
                <tr>
                  <th>{t("nar.col.a")}</th>
                  <th>{t("nar.col.b")}</th>
                  <th>{t("nar.col.rel")}</th>
                  <th>{t("nar.col.force")}</th>
                  <th>{t("nar.col.hits")}</th>
                </tr>
              </thead>
              <tbody>
                {data.pairs.map((p) => (
                  <tr key={`${p.a}-${p.b}`}>
                    <td>{p.a_label}</td>
                    <td>{p.b_label}</td>
                    <td>{p.relation}</td>
                    <td>{p.force}</td>
                    <td>{p.count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="muted">{t("nar.noPairs")}</p>
        )}
      </section>
      ) : null}
    </div>
  );
}

function Dossier({
  n,
  onReview,
  note,
  compact,
}: {
  n: NarrativeDossier;
  onReview: (label: string) => void;
  note: string;
  compact?: boolean;
}) {
  const { t } = useLocale();
  const series = n.series || [];
  return (
    <section className="viz narrative-dossier">
      <h3>{n.label}</h3>
      <p className="ficha-lead">{n.description}</p>
      <p className="muted">
        {t("nar.pubs", {
          state: n.state_label || n.state || "—",
          n: n.volume,
          countries: n.country_n ?? 0,
          sources: n.sources_n ?? 0,
          first: n.first_seen || "—",
        })}{" "}
        {n.origin_note}
      </p>
      {n.priority ? (
        <p>
          {t("nar.priorityLine")} <strong>{n.priority.label}</strong>. {n.priority.why}
        </p>
      ) : null}
      {n.classification ? (
        <p>
          {t("nar.classLine")} <strong>{n.classification.label}</strong>. {n.classification.why}
        </p>
      ) : null}
      {n.contrast_level ? (
        <p className="muted">
          {t("nar.contrastLine", { n: n.contrast_level.level })} {n.contrast_level.label}
        </p>
      ) : null}

      {!compact && series.length ? (
        <>
          <h4>{t("nar.time")}</h4>
          <MiniBars values={series.map((p) => p.count)} />
          <p className="muted">
            {t("nar.range", { from: series[0]?.day || "—", to: series[series.length - 1]?.day || "—" })}{" "}
            {t("nar.peak")} {series.reduce((a, b) => (b.count > a.count ? b : a), series[0]).day}.
          </p>
        </>
      ) : null}

      {!compact && (n.semantic_stages || []).length ? (
        <>
          <h4>{t("nar.semantic")}</h4>
          <ol className="method-list">
            {n.semantic_stages?.map((s) => (
              <li key={s.stage}>
                {t("nar.stage", { n: s.stage, from: s.from || "—", to: s.to || "—" })} {s.concepts.join(" → ") || t("nar.noBank")}
              </li>
            ))}
          </ol>
        </>
      ) : null}

      {!compact && (n.claims || []).length ? (
        <>
          <h4>{t("nar.claims")}</h4>
          <div className="source-table-wrap">
            <table className="source-table">
              <thead>
                <tr>
                  <th>{t("nar.col.text")}</th>
                  <th>{t("nar.col.mod")}</th>
                  <th>{t("nar.col.nli")}</th>
                </tr>
              </thead>
              <tbody>
                {n.claims?.slice(0, 12).map((c) => (
                  <tr key={c.claim_id || c.text}>
                    <td>{c.text}</td>
                    <td>{c.modality || "—"}</td>
                    <td>{c.nli_label || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : null}

      {!compact && (n.evidence || []).length ? (
        <>
          <h4>{t("nar.evidence")}</h4>
          <ul className="method-list">
            {n.evidence?.slice(0, 10).map((e) => (
              <li key={e.evidence_id || e.url}>
                {e.official ? t("origin.oficial") : e.source_tier || t("common.source")} · {e.host || e.url} · {e.stance || "—"}
                {e.snippet ? ` — ${e.snippet}` : ""}
              </li>
            ))}
          </ul>
        </>
      ) : null}

      {!compact && (n.propagation || []).length ? (
        <>
          <h4>{t("nar.prop")}</h4>
          <p className="muted">{t("nar.propLead")}</p>
          <div className="source-table-wrap">
            <table className="source-table">
              <thead>
                <tr>
                  <th>{t("filter.country")}</th>
                  <th>{t("nar.col.first")}</th>
                  <th>{t("nar.col.pubs")}</th>
                  <th>{t("nar.col.sources")}</th>
                  <th>{t("nar.col.peak")}</th>
                </tr>
              </thead>
              <tbody>
                {n.propagation?.map((p) => (
                  <tr key={p.country}>
                    <td>{p.country}</td>
                    <td>{p.first_seen || "—"}</td>
                    <td>{p.publications}</td>
                    <td>{p.sources}</td>
                    <td>{p.peak || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : null}

      {!compact && (n.articles || []).length ? (
        <>
          <h4>{t("nar.notes")}</h4>
          <ul className="method-list">
            {n.articles?.map((a) => (
              <li key={a.content_id}>
                <Link to={`/article/${encodeURIComponent(a.content_id)}`}>{a.title || a.content_id}</Link>
              </li>
            ))}
          </ul>
        </>
      ) : null}

      {!compact ? (
        <>
          <div className="filter-row">
            <button type="button" className="chip" onClick={() => onReview("continuar_monitoreo")}>
              {t("nar.watch")}
            </button>
            <button type="button" className="chip" onClick={() => onReview("necesita_evidencia")}>
              {t("nar.need")}
            </button>
            <button type="button" className="chip" onClick={() => onReview("descartado")}>
              {t("nar.false")}
            </button>
          </div>
          {note ? <p className="muted">{note}</p> : null}
        </>
      ) : null}
    </section>
  );
}
