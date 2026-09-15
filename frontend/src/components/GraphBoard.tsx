import { useMemo, useState } from "react";
import type { GraphEdge, GraphNode } from "../api";
import NetworkGraph from "./NetworkGraph";

const KIND: Record<string, string> = {
  source: "Fuente",
  disease: "Enfermedad",
  narrative: "Relato",
  article: "Nota",
  similar: "Nota cercana",
};

function prune(nodes: GraphNode[], edges: GraphEdge[], limit = 42) {
  if (nodes.length <= limit) return { nodes, edges };
  const keep = [...nodes].sort((a, b) => (b.value || 0) - (a.value || 0)).slice(0, limit);
  const ids = new Set(keep.map((n) => n.id));
  return { nodes: keep, edges: edges.filter((e) => ids.has(e.from) && ids.has(e.to)) };
}

function relationOf(edge: GraphEdge, byId: Map<string, GraphNode>): string {
  if (edge.label) return edge.label;
  const a = byId.get(edge.from)?.group;
  const b = byId.get(edge.to)?.group;
  const g = new Set([a, b]);
  if (g.has("source") && g.has("disease")) return "habla de";
  if (g.has("article") && g.has("source")) return "publicó";
  if (g.has("article") && g.has("disease")) return "menciona";
  if (g.has("disease") && g.has("narrative")) return "entra en";
  if (g.has("source") && g.has("narrative")) return "alimenta";
  return "relaciona";
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
          relation: relationOf(e, byId),
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
  }, [view.edges, byId, picked, q]);

  if (!view.nodes.length) {
    return (
      <section className="viz">
        <h3>Sin red en este recorte</h3>
        <p className="muted">Cuando haya notas con fuente y enfermedad, aparecen aquí como puntos unidos.</p>
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
        Cada punto es una fuente, una enfermedad o un relato. Cuanto más grande, más notas lo mencionan. La tabla de
        al lado lista las mismas uniones: pulsa una fila para saltar de un nodo al otro.
      </p>
      <p className="graph-legend">
        <span>
          <i className="swatch source" /> Fuente
        </span>
        <span>
          <i className="swatch disease" /> Enfermedad
        </span>
        <span>
          <i className="swatch narrative" /> Relato
        </span>
        {sample != null ? (
          <span className="muted">
            {sample} de {universe ?? "?"} notas
            {nodes.length > view.nodes.length ? ` · ${view.nodes.length} puntos más citados` : ""}
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
            <h4>Relaciones</h4>
            <p className="muted">
              {picked ? `${rows.length} de este punto` : `${rows.length} uniones`}
            </p>
            <input
              type="search"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Buscar nodo o relación"
              aria-label="Buscar en la tabla de relaciones"
            />
            {picked ? (
              <button type="button" className="ghost" onClick={() => setPicked(null)}>
                Ver todas
              </button>
            ) : null}
          </div>
          <div className="graph-rels-body">
            {rows.length ? (
              <table>
                <thead>
                  <tr>
                    <th>De</th>
                    <th>Relación</th>
                    <th>A</th>
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
                        <em>{KIND[r.from!.group] || r.from!.group}</em>
                      </td>
                      <td className="rel">{r.relation}</td>
                      <td>
                        <strong>{r.to!.label}</strong>
                        <em>{KIND[r.to!.group] || r.to!.group}</em>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="muted">Ninguna unión coincide.</p>
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
              · {KIND[picked.group] || picked.group}
              {picked.value ? ` · ${picked.value} notas` : ""}
            </em>
          </span>
          <button type="button" className="run" onClick={() => onNode(picked)}>
            Ver en la sala
          </button>
        </p>
      ) : (
        <p className="muted">Pulsa un punto o una fila. Luego “Ver en la sala”.</p>
      )}
    </section>
  );
}
