import { useEffect, useRef } from "react";
import { DataSet, Network } from "vis-network/standalone";
import type { GraphEdge, GraphNode } from "../api";

const COLORS: Record<string, string> = {
  source: "#38bdf8",
  disease: "#2dd4bf",
  narrative: "#fbbf24",
  article: "#34d399",
  similar: "#cbd5e1",
};

type Props = {
  nodes: GraphNode[];
  edges: GraphEdge[];
  height?: number;
  onNode?: (node: GraphNode) => void;
};

export default function NetworkGraph({ nodes, edges, height = 480, onNode }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const onNodeRef = useRef(onNode);
  onNodeRef.current = onNode;

  useEffect(() => {
    if (!ref.current) return;
    const data = {
      nodes: new DataSet(
        nodes.map((n) => ({
          id: n.id,
          label: n.label,
          value: n.value || 1,
          group: n.group,
          title: `Pulsa para ver en la sala · ${n.label}`,
          color: {
            background: COLORS[n.group] || "#94a3b8",
            border: "#e2e8f0",
            highlight: { background: "#f8fafc", border: "#2dd4bf" },
            hover: { background: "#f0fdfa", border: "#5eead4" },
          },
          font: { color: "#f1f5f9", size: 13, face: "IBM Plex Sans" },
          borderWidth: 2,
        }))
      ),
      edges: new DataSet(
        edges.map((e, i) => ({
          id: `${e.from}-${e.to}-${i}`,
          from: e.from,
          to: e.to,
          label: e.label || "",
          color: { color: "#334155", highlight: "#2dd4bf", hover: "#5eead4" },
          font: { color: "#94a3b8", size: 10, strokeWidth: 0 },
        }))
      ),
    };
    const network = new Network(ref.current, data, {
      physics: { stabilization: { iterations: 90 }, barnesHut: { gravitationalConstant: -3200, springLength: 130 } },
      interaction: { hover: true, tooltipDelay: 40, navigationButtons: false, keyboard: false },
      nodes: { shape: "dot", scaling: { min: 12, max: 36 }, chosen: true },
      edges: { smooth: true, width: 1.4 },
    });
    network.on("click", (params) => {
      const nid = params.nodes?.[0];
      if (!nid) return;
      const node = nodes.find((n) => String(n.id) === String(nid));
      if (node) onNodeRef.current?.(node);
    });
    network.on("hoverNode", () => {
      if (ref.current) ref.current.style.cursor = "pointer";
    });
    network.on("blurNode", () => {
      if (ref.current) ref.current.style.cursor = "grab";
    });
    return () => network.destroy();
  }, [nodes, edges]);

  return <div ref={ref} className="graph-host clickable" style={{ height, minHeight: 420 }} />;
}
