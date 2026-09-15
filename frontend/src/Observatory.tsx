import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import {
  api,
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
import BanksPanel from "./components/BanksPanel";
import ChartsPanel from "./components/ChartsPanel";
import GraphBoard from "./components/GraphBoard";
import MapBoard from "./components/MapBoard";
import NarrativesPanel from "./components/NarrativesPanel";
import ReviewBoard from "./components/ReviewBoard";
import SourcesPanel from "./components/SourcesPanel";
import { MiniBars, Sparkline } from "./components/Sparkline";
import { articleHref } from "./safeUrl";
import { ensureGeoPoints } from "./geoCentroids";
import {
  DISEASE_VISUAL,
  KIND_LABEL,
  cardExcerpt,
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
  if (pathname.startsWith("/revision") || pathname.startsWith("/alertas") || pathname.startsWith("/afirmaciones") || pathname.startsWith("/evidencia")) {
    return "revision";
  }
  if (pathname.startsWith("/mapa")) return "mapa";
  if (pathname.startsWith("/graficas")) return "graficas";
  if (pathname.startsWith("/grafo")) return "grafo";
  if (pathname.startsWith("/fuentes") || pathname.startsWith("/bancos")) return "fuentes";
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
  const [alertsReady, setAlertsReady] = useState(false);
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
    try {
      const results = await Promise.allSettled([
        api.stats(query),
        api.geo(query),
        api.charts(query),
        api.graph(query),
        api.articles(query, filters.page, PAGE_SIZE),
        api.sources(),
        api.diseases(),
      ]);
      const ok = <T,>(i: number): T | null =>
        results[i].status === "fulfilled" ? (results[i].value as T) : null;
      if (results.every((r) => r.status === "rejected")) {
        setErr("No se pudo conectar con el servidor. Inténtalo de nuevo en unos segundos.");
        return;
      }
      setErr("");
      const st = ok<Awaited<ReturnType<typeof api.stats>>>(0);
      const g = ok<Awaited<ReturnType<typeof api.geo>>>(1);
      const ch = ok<ChartBundle>(2);
      const gr = ok<{ nodes: GraphNode[]; edges: GraphEdge[]; sample?: number; universe?: number }>(3);
      const arts = ok<{ articles: Article[]; count: number }>(4);
      const srcs = ok<{ sources: SourceRow[] }>(5);
      const dis = ok<{ diseases: DiseaseCard[] }>(6);
      if (st) {
        setKpis(st.kpis);
        setSparks(st.sparklines || {});
        setDiseases(dis?.diseases?.length ? dis.diseases : st.diseases || []);
        setMine(st.mine || null);
        setMysqlOn(Boolean(st.mysql ?? st.kpis?.mysql));
        setMysqlStale(Boolean(st.mysql_stale ?? st.kpis?.mysql_stale));
      } else if (dis?.diseases?.length) {
        setDiseases(dis.diseases);
      }
      if (arts) {
        const rows = arts.articles || [];
        setArticles(rows);
        setArticleCount(arts.count ?? rows.length);
        if (g) {
          const points = ensureGeoPoints(
            g.points?.length ? g.points : (g.countries || []).filter((c) => !c.unlocated),
            rows
          );
          setGeo(points);
          setUnlocated(g.unlocated || (g.countries || []).filter((c) => c.unlocated));
        }
      } else if (g) {
        setGeo(ensureGeoPoints(g.points?.length ? g.points : (g.countries || []).filter((c) => !c.unlocated), []));
        setUnlocated(g.unlocated || (g.countries || []).filter((c) => c.unlocated));
      }
      if (ch) setCharts(ch);
      if (gr) setGraph(gr);
      if (srcs) setSources(srcs.sources || []);
    } catch {
      setErr("No se pudo conectar con el servidor. Inténtalo de nuevo en unos segundos.");
    }
    try {
      const al = await api.alerts("pending_review");
      setAlerts(al.alerts || []);
      setAlertsReady(true);
    } catch {
      /* conservar la cola que ya se ve */
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
    sala: { title: "Sala de vigilancia", subtitle: "Documentos y relatos agrupados, por fecha de publicación." },
    revision: { title: "Revisión", subtitle: "Una nota a la vez: afirmación, evidencia, decisión." },
    mapa: { title: "Mapa de menciones", subtitle: "Lugares que nombran las notas. Pulsa un punto y ábrelo en la sala." },
    graficas: { title: "Gráficas", subtitle: "Volumen, veredictos y evolución de los relatos. Una palabra no declara falsedad." },
    grafo: { title: "Grafo", subtitle: "Puntos unidos por notas en común. Pulsa uno y ábrelo en la sala." },
    fuentes: { title: "Fuentes", subtitle: "Catálogo, las que sí se usaron en el contraste, y el banco de términos." },
  };

  const capture = kpis;
  const bannerClass = mysqlStale || (!mysqlOn && capture?.mysql === false) ? "banner mine-banner warn" : "banner mine-banner";
  const focus = panel === "revision" || panel === "grafo";

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
      {focus && err ? <p className="banner err">{err}</p> : null}
      {panel !== "sala" && !focus && err && <p className="banner err">{err}</p>}
      {panel !== "sala" && !focus && note && <p className="banner">{note}</p>}
      {panel !== "sala" && !focus ? (
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

      {panel === "sala" ? (
        <>
          {err ? <p className="banner err">{err}</p> : null}
          {note ? <p className="banner">{note}</p> : null}
        </>
      ) : !focus ? (
      <section className="kpis" aria-label="Indicadores">
        <Kpi label="Artículos" value={kpis?.articles ?? "—"} series={sparks.articles} />
        <Kpi label="Afirmaciones" value={kpis?.claims ?? "—"} series={sparks.articles} color="#34d399" bars />
        <Kpi label="Alertas pendientes" value={kpis?.alerts_pending ?? "—"} series={sparks.articles} color="#f87171" accent />
        <Kpi label="Fuentes" value={kpis?.sources ?? "—"} series={sparks.articles} />
      </section>
      ) : null}

      {!focus ? (
      <>
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
      </>
      ) : null}

      {panel === "sala" && (
        <>
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
          <NarrativesPanel query={query} surface="sala" />
        </>
      )}

      {panel === "revision" && (
        <ReviewBoard
          alerts={alerts}
          pendingHint={Number(kpis?.alerts_pending || 0)}
          loading={!alertsReady}
          onDone={load}
        />
      )}

      {panel === "mapa" && (
        <section className="map-wall">
          <MapBoard
            points={geo}
            unlocated={unlocated}
            onOpenSala={(p) => {
              const placeQuery = p.grain === "place" ? p.query || p.name : null;
              navigate({
                pathname: "/",
                search: filtersToSearch({
                  ...filters,
                  country: p.country && !["XX", "INT"].includes(p.country) ? p.country : filters.country,
                  q: placeQuery || filters.q,
                  page: 1,
                }),
              });
            }}
          />
        </section>
      )}

      {panel === "graficas" && (
        <>
          <ChartsPanel data={charts} filters={filters} onPatch={patchFilters} />
          <NarrativesPanel query={query} surface="graficas" />
        </>
      )}

      {panel === "grafo" && (
        <GraphBoard
          nodes={graph.nodes}
          edges={graph.edges}
          sample={graph.sample}
          universe={graph.universe}
          onNode={onGraphNode}
        />
      )}

      {panel === "fuentes" && (
        <>
          <SourcesPanel sources={sources} filters={filters} onSaved={load} />
          <BanksPanel />
        </>
      )}
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

export { HitlButtons } from "./components/HitlButtons";

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
