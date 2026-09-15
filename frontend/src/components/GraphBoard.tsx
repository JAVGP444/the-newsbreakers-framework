import { useMemo, useState } from "react";
import type { GraphEdge, GraphNode } from "../api";
import { useLocale } from "../locale";
import NetworkGraph from "./NetworkGraph";

function prune(nodes: GraphNode[], edges: GraphEdge[], limit = 42) {
  if (nodes.length <= limit) return { nodes, edges };
  const keep = [...nodes].sort((a, b) => (b.value || 0) - (a.value || 0)).slice(0, limit);
  const ids = new Set(keep.map((n) => n.id));
  return { nodes: keep, edges: edges.filter((e) => ids.has(e.from) && ids.has(e.to)) };
}

function relationOf(
  edge: GraphEdge,
  byId: Map<string, GraphNode>,
  t: (k: string, vars?: Record<string, string | number>) => string
): string {
  if (edge.label) return edge.label;
  const a = byId.get(edge.from)?.group;
  const b = byId.get(edge.to)?.group;
  const g = new Set([a, b]);
  if (g.has("source") && g.has("disease")) return t("graph.rel.talks");
  if (g.has("article") && g.has("source")) return t("graph.rel.published");
  if (g.has("article") && g.has("disease")) return t("graph.rel.mentions");
  if (g.has("disease") && g.has("narrative")) return t("graph.rel.enters");
  if (g.has("source") && g.has("narrative")) return t("graph.rel.feeds");
  return t("graph.rel.relates");
}

export default function GraphBoard({
  nodes,
  edges,
  sample,
  universe,
  onNode,
}: {
  nodes: GraphNode[];
  edges: GraphEdge[];
  sample?: number;
  universe?: number;
  onNode: (node: GraphNode) => void;
}) {
  const { t } = useLocale();
  const kindOf = (group?: string) => {
    if (!group) return "";
    const hit = t(`graph.kind.${group}`);
    return hit.startsWith("graph.kind.") ? group : hit;
  };
  const [picked, setPicked] = useState<GraphNode | null>(null);
  const [q, setQ] = useState("");
  const view = useMemo(() => prune(nodes, edges), [nodes, edges]);
  const byId = useMemo(() => new Map(view.nodes.map((n) => [n.id, n])), [view.nodes]);

  const rows = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return view.edges
      .map((e) => {
        const from = byId.get(e.from);
        const to = byId.get(e.to);
        return {
          key: `${e.from}::${e.to}`,
          from,
          to,
          relation: relationOf(e, byId, t),
        };
      })
      .filter((r) => r.from && r.to)
      .filter((r) => {
        if (picked && r.from!.id !== picked.id && r.to!.id !== picked.id) return false;
        if (!needle) return true;
        const blob = `${r.from!.label} ${r.to!.label} ${r.relation}`.toLowerCase();
        return blob.includes(needle);
      })
      .sort((a, b) => (b.from!.value || 0) + (b.to!.value || 0) - ((a.from!.value || 0) + (a.to!.value || 0)));
  }, [view.edges, byId, picked, q, t]);

  if (!view.nodes.length) {
    return (
      <section className="viz">
        <h3>{t("graph.emptyTitle")}</h3>
        <p className="muted">{t("graph.empty")}</p>
      </section>
    );
  }

  function pickFromRow(from: GraphNode, to: GraphNode) {
    const next = picked && picked.id === from.id ? to : from;
    setPicked(next);
  }

  return (
    <section className="graph-board">
      <p className="graph-howto">
        {t("graph.howto")}
      </p>
      <p className="graph-legend">
        <span>
          <i className="swatch source" /> {t("graph.kind.source")}
        </span>
        <span>
          <i className="swatch disease" /> {t("graph.kind.disease")}
        </span>
        <span>
          <i className="swatch narrative" /> {t("graph.kind.narrative")}
        </span>
        {sample != null ? (
          <span className="muted">
            {t("graph.sample", { sample, universe: universe ?? "?" })}
            {nodes.length > view.nodes.length ? t("graph.cited", { n: view.nodes.length }) : ""}
          </span>
        ) : null}
      </p>
      <div className="graph-split">
        <NetworkGraph
          nodes={view.nodes}
          edges={view.edges}
          height={560}
          hideEdgeLabels
          selectedId={picked?.id}
          onNode={setPicked}
        />
        <aside className="graph-rels" aria-label="Relaciones del grafo">
          <div className="graph-rels-head">
            <h4>{t("graph.rels")}</h4>
            <p className="muted">
              {picked ? t("graph.ofNode", { n: rows.length }) : t("graph.unions", { n: rows.length })}
            </p>
            <input
              type="search"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder={t("graph.search")}
              aria-label={t("graph.searchAria")}
            />
            {picked ? (
              <button type="button" className="ghost" onClick={() => setPicked(null)}>
                {t("graph.all")}
              </button>
            ) : null}
          </div>
          <div className="graph-rels-body">
            {rows.length ? (
              <table>
                <thead>
                  <tr>
                    <th>{t("graph.col.from")}</th>
                    <th>{t("graph.col.rel")}</th>
                    <th>{t("graph.col.to")}</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r) => (
                    <tr
                      key={r.key}
                      className={picked && (r.from!.id === picked.id || r.to!.id === picked.id) ? "on" : ""}
                      onClick={() => pickFromRow(r.from!, r.to!)}
                    >
                      <td>
                        <strong>{r.from!.label}</strong>
                        <em>{kindOf(r.from!.group)}</em>
                      </td>
                      <td className="rel">{r.relation}</td>
                      <td>
                        <strong>{r.to!.label}</strong>
                        <em>{kindOf(r.to!.group)}</em>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="muted">{t("graph.none")}</p>
            )}
          </div>
        </aside>
      </div>
      {picked ? (
        <p className="graph-pick">
          <span>
            <strong>{picked.label}</strong>
            <em>
              {" "}
              · {kindOf(picked.group)}
              {picked.value ? ` · ${t("graph.notesOf", { n: picked.value })}` : ""}
            </em>
          </span>
          <button type="button" className="run" onClick={() => onNode(picked)}>
            {t("graph.openSala")}
          </button>
        </p>
      ) : (
        <p className="muted">{t("graph.pickHint")}</p>
      )}
    </section>
  );
}
