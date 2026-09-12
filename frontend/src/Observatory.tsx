import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import {
  api,
  verdictClass,
  type AlertRow,
  type Article,
  type ChartBundle,
  type DiseaseCard,
  type GeoRow,
  type GraphEdge,
  type GraphNode,
  type Kpis,
  type MineStatus,
  type SourceRow,
} from "./api";
import AppHeader from "./components/AppHeader";
import ArticleCard from "./components/ArticleCard";
import ChartsPanel from "./components/ChartsPanel";
import LeerMas from "./components/LeerMas";
import MapView from "./components/MapView";
import NetworkGraph from "./components/NetworkGraph";
import { MiniBars, Sparkline } from "./components/Sparkline";
import { articleHref } from "./safeUrl";
import { ensureGeoPoints } from "./geoCentroids";
import {
  DISEASE_VISUAL,
  KIND_LABEL,
  cardExcerpt,
  flowText,
  stanceLabel,
  verdictLabel,
} from "./display";
import { useTranslated } from "./translate";
import {
  activeFilterChips,
  chipLabel,
  filtersToApiQuery,
  filtersToSearch,
  readFilters,
  writeFilters,
  type ObservatoryFilters,
} from "./filters";

const PAGE_SIZE = 12;
const VERDICTS = [
  { id: "", label: "Veredicto" },
  { id: "respaldado", label: "Respaldado" },
  { id: "insuficiente", label: "Insuficiente" },
  { id: "contradicho", label: "Contradicho" },
  { id: "revision_humana", label: "Revisión humana" },
  { id: "engañoso", label: "Engañoso" },
  { id: "sin_verificar", label: "Sin verificar" },
];

type Panel = "sala" | "revision" | "mapa" | "graficas" | "grafo" | "fuentes";

function panelFromPath(pathname: string): Panel {
  if (pathname.startsWith("/revision")) return "revision";
  if (pathname.startsWith("/mapa")) return "mapa";
  if (pathname.startsWith("/graficas")) return "graficas";
  if (pathname.startsWith("/grafo")) return "grafo";
  if (pathname.startsWith("/fuentes")) return "fuentes";
  return "sala";
}

function formatMineTime(iso?: string | null) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return String(iso);
  return d.toLocaleString();
}

function filterChipText(
  key: string,
  value: string,
  diseases: DiseaseCard[],
  countries: [string, string][],
  sourceNames: Map<string, string>
) {
  if (key === "disease") {
    const d = diseases.find((x) => x.id === value);
    return chipLabel(key, d?.short || d?.label || DISEASE_VISUAL[value]?.label || value.replace(/_/g, " "));
  }
  if (key === "country") {
    const name = countries.find(([code]) => code === value)?.[1];
    return chipLabel(key, name || value);
  }
  if (key === "source") return chipLabel(key, sourceNames.get(value) || value);
  if (key === "origin") return chipLabel(key, KIND_LABEL[value as keyof typeof KIND_LABEL] || value);
  if (key === "stance") return chipLabel(key, stanceLabel(value));
  if (key === "verdict") return chipLabel(key, verdictLabel(value));
  return chipLabel(key, value);
}

export default function Observatory() {
  const location = useLocation();
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const panel = panelFromPath(location.pathname);
  const filters = useMemo(() => readFilters(params), [params]);
  const query = filtersToApiQuery(filters);

  const [kpis, setKpis] = useState<Kpis | null>(null);
  const [sparks, setSparks] = useState<Record<string, number[]>>({});
  const [diseases, setDiseases] = useState<DiseaseCard[]>([]);
  const [mine, setMine] = useState<MineStatus | null>(null);
  const [mysqlOn, setMysqlOn] = useState(false);
  const [mysqlStale, setMysqlStale] = useState(false);
  const [geo, setGeo] = useState<GeoRow[]>([]);
  const [unlocated, setUnlocated] = useState<GeoRow[]>([]);
  const [charts, setCharts] = useState<ChartBundle | null>(null);
  const [graph, setGraph] = useState<{ nodes: GraphNode[]; edges: GraphEdge[]; sample?: number; universe?: number }>({
    nodes: [],
    edges: [],
  });
  const [articles, setArticles] = useState<Article[]>([]);
  const [articleCount, setArticleCount] = useState(0);
  const [sources, setSources] = useState<SourceRow[]>([]);
  const [alerts, setAlerts] = useState<AlertRow[]>([]);
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState("");
  const [err, setErr] = useState("");

  const patchFilters = useCallback(
    (next: Partial<ObservatoryFilters>) => {
      setParams(writeFilters(params, next), { replace: true });
    },
    [params, setParams]
  );

  const load = useCallback(async () => {
    setErr("");
    try {
      const [st, g, ch, gr, arts, srcs, al, dis] = await Promise.all([
        api.stats(query),
        api.geo(query),
        api.charts(query),
        api.graph(query),
        api.articles(query, filters.page, PAGE_SIZE),
        api.sources(),
        api.alerts("pending_review"),
        api.diseases(),
      ]);
      setKpis(st.kpis);
      setSparks(st.sparklines || {});
      setDiseases(dis.diseases?.length ? dis.diseases : st.diseases || []);
      setMine(st.mine || null);
      setMysqlOn(Boolean(st.mysql ?? st.kpis?.mysql));
      setMysqlStale(Boolean(st.mysql_stale ?? st.kpis?.mysql_stale));
      const rows = arts.articles || [];
      setArticles(rows);
      setArticleCount(arts.count ?? rows.length);
      const points = ensureGeoPoints(g.points?.length ? g.points : (g.countries || []).filter((c) => !c.unlocated), rows);
      setGeo(points);
      setUnlocated(g.unlocated || (g.countries || []).filter((c) => c.unlocated));
      setCharts(ch);
      setGraph(gr);
      setSources(srcs.sources || []);
      setAlerts(al.alerts || []);
    } catch {
      setErr("No se pudo conectar con el servidor. Inténtalo de nuevo en unos segundos.");
    }
  }, [query, filters.page]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    const t = window.setInterval(() => {
      load();
    }, 60_000);
    return () => window.clearInterval(t);
  }, [load]);

  const sourceNames = useMemo(() => {
    const map = new Map<string, string>();
    for (const s of sources) {
      map.set(s.source_id, s.name || s.domain || s.source_id);
    }
    return map;
  }, [sources]);

  const pageCount = Math.max(1, Math.ceil(articleCount / PAGE_SIZE));
  const pills = diseases.filter((d) => d.id !== "otras" && (d.menciones > 0 || ["gusano_barrenador", "gripe_aviar", "fiebre_porcina_clasica"].includes(d.id)));
  const other = diseases.find((d) => d.id === "otras");
  const chips = activeFilterChips(filters);
  const countries = useMemo(() => {
    const seen = new Map<string, string>();
    for (const g of [...geo, ...unlocated]) {
      if (g.country) seen.set(g.country, g.name || g.country);
    }
    return [...seen.entries()];
  }, [geo, unlocated]);

  function openArticle(id?: string | null) {
    if (!id) return;
    navigate(articleHref(id));
  }

  async function runCycle() {
    setBusy(true);
    setNote("Recolectando y analizando noticias…");
    try {
      const summary = await api.cycle();
      setNote(`Fuentes revisadas ${summary.sources_checked} · artículos nuevos ${summary.articles_new} · afirmaciones ${summary.claims}`);
      await load();
    } catch {
      setNote("El ciclo no se pudo completar. Inténtalo de nuevo.");
    } finally {
      setBusy(false);
    }
  }

  function onGraphNode(node: GraphNode) {
    if (node.group === "disease") {
      const id = node.filter?.disease || node.id.replace(/^DIS-/, "");
      patchFilters({ disease: id, page: 1 });
      navigate({ pathname: "/", search: filtersToSearch({ ...filters, disease: id, page: 1 }) });
      return;
    }
    if (node.group === "source") {
      const sid = node.source_id || node.filter?.source || node.id.replace(/^SRC-/, "");
      navigate({ pathname: "/", search: filtersToSearch({ ...filters, source: sid, page: 1 }) });
      return;
    }
    if (node.group === "narrative") {
      const q = node.filter?.q || node.label;
      navigate({ pathname: "/", search: filtersToSearch({ ...filters, q, page: 1 }) });
      return;
    }
    if (node.group === "article" || node.group === "similar") {
      openArticle(node.id);
    }
  }

  const titles: Record<Panel, { title: string; subtitle: string }> = {
    sala: { title: "Sala de vigilancia", subtitle: "Por fecha de publicación." },
    revision: { title: "Revisión humana", subtitle: "Revisa afirmaciones y evidencia, y valida o descarta cada alerta." },
    mapa: { title: "Mapa de menciones", subtitle: "Pulsa un país para ver sus documentos en la sala." },
    graficas: { title: "Gráficas", subtitle: "De qué enfermedades se habla, de dónde sale y qué concluyó el análisis." },
    grafo: { title: "Grafo de narrativas", subtitle: "Pulsa una enfermedad o una fuente para ver sus documentos en la sala." },
    fuentes: { title: "Fuentes", subtitle: "Método de captura, última visita y estado de cada medio." },
  };

  const capture = kpis;
  const bannerClass = mysqlStale || (!mysqlOn && capture?.mysql === false) ? "banner mine-banner warn" : "banner mine-banner";

  return (
    <div className="shell observatory">
      <AppHeader
        title={titles[panel].title}
        subtitle={titles[panel].subtitle}
        actions={
          <button type="button" className="run" disabled={busy} onClick={runCycle}>
            {busy ? "Ciclo en curso…" : "Ejecutar ciclo"}
          </button>
        }
      />
      {panel !== "sala" && err && <p className="banner err">{err}</p>}
      {panel !== "sala" && note && <p className="banner">{note}</p>}
      {panel !== "sala" ? (
      <p className={bannerClass}>
        {mine?.last_mine ? `Última minería: ${formatMineTime(mine.last_mine)}` : "Aún no hay corrida de minería"}
        {" · "}
        {capture?.docs != null
          ? `${capture.docs} documentos · ${capture.rss ?? 0} de RSS · ${capture.no_body ?? 0} sin texto`
          : kpis
            ? `${kpis.articles} artículos · ${kpis.claims} afirmaciones`
            : ""}
        {" · "}
        {mysqlStale
          ? `MySQL atrasado${kpis?.mysql_lag_seconds != null ? ` (${kpis.mysql_lag_seconds}s)` : ""}`
          : mysqlOn
            ? "MySQL conectado"
            : "MySQL no conectado (SQLite)"}
      </p>
      ) : null}

      {panel !== "sala" ? (
      <section className="kpis" aria-label="Indicadores">
        <Kpi label="Artículos" value={kpis?.articles ?? "—"} series={sparks.articles} />
        <Kpi label="Afirmaciones" value={kpis?.claims ?? "—"} series={sparks.articles} color="#34d399" bars />
        <Kpi label="Alertas pendientes" value={kpis?.alerts_pending ?? "—"} series={sparks.articles} color="#f87171" accent />
        <Kpi label="Fuentes" value={kpis?.sources ?? "—"} series={sparks.articles} />
      </section>
      ) : (
        <>
          {err ? <p className="banner err">{err}</p> : null}
          {note ? <p className="banner">{note}</p> : null}
        </>
      )}

      <div className="toolbar">
        <div className="disease-pills" role="group" aria-label="Filtro por enfermedad">
          <button type="button" className={!filters.disease ? "pill-btn on" : "pill-btn"} onClick={() => patchFilters({ disease: null, page: 1 })}>
            Todas
          </button>
          {pills.map((d) => (
            <button
              type="button"
              key={d.id}
              className={filters.disease === d.id ? "pill-btn on" : "pill-btn"}
              onClick={() => patchFilters({ disease: d.id, page: 1 })}
            >
              {d.short || d.label}
              <b>{d.menciones}</b>
            </button>
          ))}
          {other && other.menciones > 0 ? (
            <button type="button" className={filters.disease === "otras" ? "pill-btn on" : "pill-btn"} onClick={() => patchFilters({ disease: "otras", page: 1 })}>
              Otras <b>{other.menciones}</b>
            </button>
          ) : null}
        </div>
        <div className="filter-row">
          <label>
            Desde
            <input type="date" value={filters.from || ""} onChange={(e) => patchFilters({ from: e.target.value || null, page: 1 })} />
          </label>
          <label>
            Hasta
            <input type="date" value={filters.to || ""} onChange={(e) => patchFilters({ to: e.target.value || null, page: 1 })} />
          </label>
          <label>
            País
            <select value={filters.country || ""} onChange={(e) => patchFilters({ country: e.target.value || null, page: 1 })}>
              <option value="">Todos</option>
              {countries.map(([code, name]) => (
                <option key={code} value={code}>
                  {name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Veredicto
            <select value={filters.verdict || ""} onChange={(e) => patchFilters({ verdict: e.target.value || null, page: 1 })}>
              {VERDICTS.map((v) => (
                <option key={v.id} value={v.id}>
                  {v.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            Fuente
            <select value={filters.source || ""} onChange={(e) => patchFilters({ source: e.target.value || null, page: 1 })}>
              <option value="">Todas</option>
              {sources
                .filter((s) => (s.article_count || 0) > 0)
                .slice(0, 80)
                .map((s) => (
                  <option key={s.source_id} value={s.source_id}>
                    {s.name || s.source_id}
                  </option>
                ))}
            </select>
          </label>
          <label className="search-box">
            <span className="sr-only">Buscar</span>
            <input
              type="search"
              placeholder="Buscar título, fuente o texto…"
              value={filters.q || ""}
              onChange={(e) => patchFilters({ q: e.target.value, page: 1 })}
            />
          </label>
        </div>
      </div>
      {chips.length ? (
        <p className="filter-chips">
          {chips.map((c) => (
            <button key={String(c.key)} type="button" className="chip on" onClick={() => patchFilters({ [c.key]: c.key === "compare" ? [] : null, page: 1 })}>
              {filterChipText(c.key, c.value, diseases, countries, sourceNames)} ×
            </button>
          ))}
          <button type="button" className="chip" onClick={() => setParams(new URLSearchParams(), { replace: true })}>
            Limpiar
          </button>
        </p>
      ) : null}

      {panel === "sala" && (
        <ArticleGrid
          articles={articles}
          sourceNames={sourceNames}
          total={articleCount}
          page={filters.page}
          pageCount={pageCount}
          dbEmpty={(kpis?.docs ?? kpis?.articles ?? 0) === 0 && !filters.q && !filters.disease}
          onPage={(n) => patchFilters({ page: n })}
          onClear={() => setParams(new URLSearchParams(), { replace: true })}
        />
      )}

      {panel === "revision" && <HitlQueue alerts={alerts} onDone={load} />}

      {panel === "mapa" && (
        <section className="map-wall">
          <MapView
            points={geo}
            height={480}
            onSelect={(p) => {
              navigate({ pathname: "/", search: filtersToSearch({ ...filters, country: p.country, page: 1 }) });
            }}
          />
          <LeerMas maxItems={12} className="geo-dock">
            {geo.map((g) => (
              <button
                type="button"
                key={g.country}
                className="geo-row"
                onClick={() => navigate({ pathname: "/", search: filtersToSearch({ ...filters, country: g.country, page: 1 }) })}
              >
                <strong>{g.name}</strong>
                <span>{g.count}</span>
              </button>
            ))}
          </LeerMas>
          {unlocated.length ? (
            <LeerMas maxLines={2} className="muted unlocated-line">
              {`Sin ubicar (${unlocated.reduce((n, r) => n + (r.count || 0), 0)}): ${unlocated.map((u) => `${u.name} ${u.count}`).join(" · ")}`}
            </LeerMas>
          ) : null}
        </section>
      )}

      {panel === "graficas" && <ChartsPanel data={charts} filters={filters} onPatch={patchFilters} />}

      {panel === "grafo" && (
        <section className="canvas single">
          {graph.nodes.length ? (
            <NetworkGraph nodes={graph.nodes} edges={graph.edges} onNode={onGraphNode} />
          ) : (
            <p className="muted">No hay co-ocurrencias con este filtro.</p>
          )}
          <p className="muted legend-line">
            <i className="swatch source" /> fuente <i className="swatch disease" /> enfermedad{" "}
            <i className="swatch narrative" /> narrativa
            {graph.sample != null ? ` · ${graph.sample} de ${graph.universe ?? "?"} artículos` : ""}
          </p>
        </section>
      )}

      {panel === "fuentes" && <SourcesPanel sources={sources} filters={filters} />}
    </div>
  );
}

function ArticleGrid({
  articles,
  sourceNames,
  total,
  page,
  pageCount,
  dbEmpty,
  onPage,
  onClear,
}: {
  articles: Article[];
  sourceNames: Map<string, string>;
  total: number;
  page: number;
  pageCount: number;
  dbEmpty: boolean;
  onPage: (n: number) => void;
  onClear: () => void;
}) {
  const titles = articles.map((a) => a.title || a.url || a.content_id);
  const summaries = articles.map((a) => cardExcerpt(a.text, a.title));
  const tTitles = useTranslated(titles);
  const tSummaries = useTranslated(summaries);

  return (
    <section className="sala-list">
        <p className="muted list-count">
        {total} documentos
      </p>
      <div className="art-cards">
        {articles.map((a, i) => (
          <ArticleCard
            key={a.content_id}
            article={a}
            sourceName={sourceNames.get(a.source_id)}
            title={tTitles[i]}
            summary={tSummaries[i]}
          />
        ))}
      </div>
      {!articles.length && dbEmpty && <p className="muted">Aún no hay documentos. Ejecuta un ciclo desde la sala.</p>}
      {!articles.length && !dbEmpty && (
        <p className="muted">
          0 documentos con este filtro.{" "}
          <button type="button" className="chip" onClick={onClear}>
            Limpiar
          </button>
        </p>
      )}
      {pageCount > 1 && (
        <div className="pager">
          <button type="button" disabled={page <= 1} onClick={() => onPage(page - 1)}>
            Anterior
          </button>
          <span>
            {page} / {pageCount}
          </span>
          <button type="button" disabled={page >= pageCount} onClick={() => onPage(page + 1)}>
            Siguiente
          </button>
        </div>
      )}
    </section>
  );
}

function SourcesPanel({ sources, filters }: { sources: SourceRow[]; filters: ObservatoryFilters }) {
  const [open, setOpen] = useState(false);
  if (!sources.length) return <p className="muted">Todavía no hay fuentes en el catálogo.</p>;
  const preview = 12;
  const extra = sources.length > preview;
  const rows = open || !extra ? sources : sources.slice(0, preview);
  return (
    <section className="source-table-wrap">
      <table className="source-table">
        <thead>
          <tr>
            <th>Fuente</th>
            <th>Método</th>
            <th>Última captura</th>
            <th>Fallos</th>
            <th>Artículos</th>
            <th>Estado</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((s) => {
            const status = s.status || (s.last_error ? "error" : "ok");
            const label = status === "deferred" ? "Diferida" : status === "error" ? s.last_error || "Error" : "Operativa";
            return (
              <tr key={s.source_id}>
                <td>
                  <Link to={{ pathname: "/", search: filtersToSearch({ ...filters, source: s.source_id, page: 1 }) }}>
                    {s.name || s.source_id}
                  </Link>
                  <div className="muted">{s.domain}</div>
                </td>
                <td>{s.access_method || s.type || "—"}</td>
                <td>{s.last_checked ? formatMineTime(s.last_checked) : "Nunca"}</td>
                <td>{s.consecutive_failures || 0}</td>
                <td>{s.article_count ?? 0}</td>
                <td className={`source-health ${status}`}>{label}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
      {extra ? (
        <button type="button" className="leer-mas-btn" onClick={() => setOpen((v) => !v)}>
          {open ? "Leer menos" : "Leer más"}
        </button>
      ) : null}
    </section>
  );
}

function HitlQueue({ alerts, onDone }: { alerts: AlertRow[]; onDone: () => Promise<void> }) {
  const [busyId, setBusyId] = useState("");
  const [note, setNote] = useState("");
  const [editId, setEditId] = useState("");
  const [reason, setReason] = useState("");

  async function act(id: string, label: string, why = "") {
    if (label === "modificado" && !why.trim()) {
      setEditId(id);
      return;
    }
    setBusyId(id);
    setNote("");
    try {
      await api.review(id, label, why);
      setNote(`Revisión guardada: ${label}`);
      setEditId("");
      setReason("");
      await onDone();
    } catch (e) {
      setNote(e instanceof Error ? e.message : "No se pudo guardar la revisión. Inténtalo de nuevo.");
    } finally {
      setBusyId("");
    }
  }

  if (!alerts.length) return <p className="muted">No hay alertas pendientes de revisión.</p>;
  return (
    <section className="hitl-list">
      {note ? <p className="banner">{note}</p> : null}
      <p className="muted list-count">{alerts.length} en cola</p>
      <LeerMas maxItems={6}>
        {alerts.map((a) => (
          <article key={a.alert_id} className="hitl-card hitl-rich">
            <div>
              <Link to={articleHref(a.content_id)}>{a.title || a.content_id}</Link>
              <p className="art-meta">
                <span className={`pill ${verdictClass(a.verdict)}`}>{a.verdict}</span>
                <span>riesgo {a.risk_score}</span>
                <span>{a.created_at?.slice(0, 16) || ""}</span>
              </p>
              {a.primary_claim ? (
                <div className="hitl-claim">
                  <strong>Afirmación: </strong>
                  <LeerMas maxLines={3}>{flowText(a.primary_claim)}</LeerMas>
                </div>
              ) : (
                <p className="muted">Sin afirmación extraída.</p>
              )}
              {a.evidence_snippet ? (
                <div className="hitl-ev">
                  <strong>Evidencia: </strong>
                  <LeerMas maxLines={3}>{flowText(a.evidence_snippet)}</LeerMas>
                </div>
              ) : (
                <p className="muted">Sin evidencia oficial disponible.</p>
              )}
              {a.human_reason ? (
                <p className="muted">Nota del analista: {a.human_reason}</p>
              ) : null}
              {editId === a.alert_id ? (
                <label className="hitl-reason">
                  Motivo (obligatorio)
                  <textarea value={reason} onChange={(e) => setReason(e.target.value)} rows={3} />
                  <button type="button" className="run" disabled={!reason.trim() || busyId === a.alert_id} onClick={() => act(a.alert_id, "modificado", reason)}>
                    Guardar modificación
                  </button>
                </label>
              ) : null}
            </div>
            <HitlButtons busy={busyId === a.alert_id} onAct={(label) => act(a.alert_id, label)} />
          </article>
        ))}
      </LeerMas>
    </section>
  );
}

export function HitlButtons({
  busy,
  onAct,
}: {
  busy?: boolean;
  onAct: (label: "validado" | "descartado" | "modificado") => void;
}) {
  return (
    <div className="hitl-actions">
      <button type="button" className="run" disabled={busy} onClick={() => onAct("validado")}>
        Validar
      </button>
      <button type="button" className="hitl-discard" disabled={busy} onClick={() => onAct("descartado")}>
        Descartar
      </button>
      <button type="button" className="hitl-edit" disabled={busy} onClick={() => onAct("modificado")}>
        Modificar
      </button>
    </div>
  );
}

function Kpi({
  label,
  value,
  series,
  color,
  accent,
  bars,
}: {
  label: string;
  value: number | string;
  series?: number[];
  color?: string;
  accent?: boolean;
  bars?: boolean;
}) {
  return (
    <div className={`kpi ${accent ? "accent" : ""}`}>
      <span>{label}</span>
      <strong>{value}</strong>
      {bars ? <MiniBars values={series || [0]} color={color} /> : <Sparkline values={series || [0]} color={color} />}
    </div>
  );
}
