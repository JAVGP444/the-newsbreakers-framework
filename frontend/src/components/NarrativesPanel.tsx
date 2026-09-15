import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type NarrativeDossier, type NarrativeOverview } from "../api";
import NarrativeCharts from "./NarrativeCharts";
import NetworkGraph from "./NetworkGraph";
import { MiniBars } from "./Sparkline";

const FORCE_OPTS = [
  { id: "1", label: "Toda fuerza" },
  { id: "3", label: "Media o más (3–5)" },
  { id: "4", label: "Alta (4–5)" },
];

export type NarrativeSurface = "sala" | "revision" | "graficas" | "grafo";

export default function NarrativesPanel({ query, surface = "sala" }: { query: string; surface?: NarrativeSurface }) {
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
        if (!cancelled) setErr("No se pudieron cargar los relatos agrupados.");
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
      setNote(`Revisión guardada: ${label}. No es un sello de malicia.`);
    } catch (e) {
      setNote(e instanceof Error ? e.message : "No se pudo guardar.");
    }
  }

  if (err) return <p className="banner err">{err}</p>;
  if (!data) return <p className="muted">Cargando relatos…</p>;

  const onSala = surface === "sala";
  const onRevision = surface === "revision";
  const onGraficas = surface === "graficas";
  const onGrafo = surface === "grafo";

  return (
    <div className="narrative-stack">
      {onSala || onRevision ? (
        <p className="muted">
          {data.principle} Recorte: {data.sample} notas. Fuentes disponibles: {data.sources_available ?? "—"} · usadas
          en contraste: {data.sources_used ?? "—"}.
        </p>
      ) : null}

      {onSala && data.kpis ? (
        <section className="kpis" aria-label="Narrativas">
          <div className="kpi">
            <span>Relatos</span>
            <strong>{data.kpis.narratives ?? 0}</strong>
          </div>
          <div className="kpi">
            <span>En crecimiento</span>
            <strong>{data.kpis.growing ?? 0}</strong>
          </div>
          <div className="kpi">
            <span>Prioridad alta</span>
            <strong>{data.kpis.priority ?? 0}</strong>
          </div>
          <div className="kpi">
            <span>Afirmaciones</span>
            <strong>{data.kpis.claims ?? 0}</strong>
          </div>
        </section>
      ) : null}

      {onRevision && (data.alerts || []).length ? (
        <section className="viz">
          <h3>Alertas de relato</h3>
          <p className="muted">Piden análisis. No confirman desinformación.</p>
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
        <h3>Relatos agrupados</h3>
        <p className="muted">Un relato puede reunir muchas notas que dicen esencialmente lo mismo.</p>
        {(data.narratives || []).length ? (
          <div className="source-table-wrap">
            <table className="source-table">
              <thead>
                <tr>
                  <th>Relato</th>
                  <th>Estado</th>
                  <th>Notas</th>
                  <th>Crecimiento</th>
                  <th>Prioridad</th>
                  <th>Contraste</th>
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
          <p className="muted">Aún no hay relatos agrupados en este recorte.</p>
        )}
      </section>
      ) : null}

      {(onSala || onRevision) && dossier ? <Dossier n={dossier} onReview={review} note={note} compact={onSala} /> : null}

      {onGrafo ? (
      <section className="viz">
        <h3>Conceptos del relato</h3>
        <div className="filter-row">
          <label>
            Categoría
            <select value={category} onChange={(e) => setCategory(e.target.value)}>
              <option value="">Todas</option>
              {(data.categories || []).map((c) => (
                <option key={c.id} value={c.id}>
                  {c.label} ({c.count})
                </option>
              ))}
            </select>
          </label>
          <label>
            Fuerza mínima
            <select value={forceMin} onChange={(e) => setForceMin(e.target.value)}>
              {FORCE_OPTS.map((o) => (
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
          <p className="muted">No hay co-ocurrencias con este recorte.</p>
        )}
      </section>
      ) : null}

      {onGraficas ? <NarrativeCharts data={data} /> : null}

      {onGrafo ? (
      <section className="viz">
        <h3>Relaciones</h3>
        {data.pairs.length ? (
          <div className="source-table-wrap">
            <table className="source-table">
              <thead>
                <tr>
                  <th>Nodo A</th>
                  <th>Nodo B</th>
                  <th>Relación</th>
                  <th>Fuerza</th>
                  <th>Apariciones</th>
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
          <p className="muted">Sin pares con este recorte.</p>
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
  const series = n.series || [];
  return (
    <section className="viz narrative-dossier">
      <h3>{n.label}</h3>
      <p className="ficha-lead">{n.description}</p>
      <p className="muted">
        {n.state_label || n.state} · {n.volume} publicaciones · {n.country_n ?? 0} países · {n.sources_n ?? 0}{" "}
        fuentes · primera aparición detectada {n.first_seen || "—"}. {n.origin_note}
      </p>
      {n.priority ? (
        <p>
          Prioridad de investigación: <strong>{n.priority.label}</strong>. {n.priority.why}
        </p>
      ) : null}
      {n.classification ? (
        <p>
          Caracterización: <strong>{n.classification.label}</strong>. {n.classification.why}
        </p>
      ) : null}
      {n.contrast_level ? (
        <p className="muted">
          Nivel de contraste {n.contrast_level.level}/5: {n.contrast_level.label}
        </p>
      ) : null}

      {!compact && series.length ? (
        <>
          <h4>Evolución temporal</h4>
          <MiniBars values={series.map((p) => p.count)} />
          <p className="muted">
            {series[0]?.day} → {series[series.length - 1]?.day}. Pico:{" "}
            {series.reduce((a, b) => (b.count > a.count ? b : a), series[0]).day}.
          </p>
        </>
      ) : null}

      {!compact && (n.semantic_stages || []).length ? (
        <>
          <h4>Evolución semántica</h4>
          <ol className="method-list">
            {n.semantic_stages?.map((s) => (
              <li key={s.stage}>
                Etapa {s.stage} ({s.from} – {s.to}): {s.concepts.join(" → ") || "sin señales del banco"}
              </li>
            ))}
          </ol>
        </>
      ) : null}

      {!compact && (n.claims || []).length ? (
        <>
          <h4>Afirmaciones</h4>
          <div className="source-table-wrap">
            <table className="source-table">
              <thead>
                <tr>
                  <th>Texto</th>
                  <th>Modalidad</th>
                  <th>NLI</th>
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
          <h4>Evidencia usada</h4>
          <ul className="method-list">
            {n.evidence?.slice(0, 10).map((e) => (
              <li key={e.evidence_id || e.url}>
                {e.official ? "Oficial" : e.source_tier || "Fuente"} · {e.host || e.url} · {e.stance || "—"}
                {e.snippet ? ` — ${e.snippet}` : ""}
              </li>
            ))}
          </ul>
        </>
      ) : null}

      {!compact && (n.propagation || []).length ? (
        <>
          <h4>Propagación por país</h4>
          <p className="muted">El primer país detectado no es origen causal.</p>
          <div className="source-table-wrap">
            <table className="source-table">
              <thead>
                <tr>
                  <th>País</th>
                  <th>Primera aparición</th>
                  <th>Publicaciones</th>
                  <th>Fuentes</th>
                  <th>Pico</th>
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
          <h4>Notas del relato</h4>
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
              Continuar monitoreando
            </button>
            <button type="button" className="chip" onClick={() => onReview("necesita_evidencia")}>
              Necesita más evidencia
            </button>
            <button type="button" className="chip" onClick={() => onReview("descartado")}>
              Falso positivo
            </button>
          </div>
          {note ? <p className="muted">{note}</p> : null}
        </>
      ) : null}
    </section>
  );
}
