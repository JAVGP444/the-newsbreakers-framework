import { useEffect, useMemo, useState } from "react";
import type { GeoRow } from "../api";
import { MAP_DISEASE_COLOR, mapDiseaseStyle, riskHint } from "../display";
import { pointKey } from "../geoCentroids";
import MapView from "./MapView";

function diseaseLabel(row: GeoRow) {
  return mapDiseaseStyle(row.disease || row.diseases?.[0]).label;
}

function grainLabel(row: GeoRow) {
  return row.grain === "place" ? "Lugar en la nota" : "País";
}

export default function MapBoard({
  points,
  unlocated,
  onOpenSala,
}: {
  points: GeoRow[];
  unlocated: GeoRow[];
  onOpenSala: (point: GeoRow) => void;
}) {
  const [picked, setPicked] = useState<GeoRow | null>(null);
  const [q, setQ] = useState("");

  useEffect(() => {
    if (!picked) return;
    if (!points.some((p) => pointKey(p) === pointKey(picked))) setPicked(null);
  }, [points, picked]);

  const rows = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return points.filter((p) => {
      if (!needle) return true;
      const blob = `${p.name} ${p.country} ${p.disease || ""} ${(p.diseases || []).join(" ")}`.toLowerCase();
      return blob.includes(needle);
    });
  }, [points, q]);

  const locatedNotes = points.reduce((n, p) => n + (p.count || 0), 0);
  const lostNotes = unlocated.reduce((n, r) => n + (r.count || 0), 0);
  const hot = points.find((p) => (p.risk_mean || 0) >= 70);

  if (!points.length && !unlocated.length) {
    return (
      <section className="viz">
        <h3>Sin lugares en este recorte</h3>
        <p className="muted">Cuando una nota nombre un país o un estado, aparece aquí como punto.</p>
      </section>
    );
  }

  return (
    <section className="graph-board map-board">
      <p className="graph-howto">
        Cada punto es un lugar que las notas nombran: un estado o condado si el texto lo dice, si no el país. El tamaño
        es cuántas notas hablan de ahí, no la gravedad del brote. El color sigue la enfermedad más citada. Un aro ámbar
        marca promedio de riesgo alto en las fichas.
      </p>
      <p className="graph-legend">
        {Object.entries(MAP_DISEASE_COLOR).map(([id, meta]) => (
          <span key={id}>
            <i className="swatch" style={{ background: meta.fill }} /> {meta.label}
          </span>
        ))}
        <span>
          <i className="swatch" style={{ background: "#94a3b8" }} /> Varias o sin etiqueta
        </span>
        <span className="muted">
          {points.length} lugares · {locatedNotes} notas ubicadas
          {lostNotes ? ` · ${lostNotes} sin ubicar` : ""}
          {hot ? ` · mayor riesgo: ${hot.name}` : ""}
        </span>
      </p>
      <div className="graph-split">
        <MapView points={points} height={560} selectedId={picked ? pointKey(picked) : null} onSelect={setPicked} />
        <aside className="graph-rels" aria-label="Lugares del mapa">
          <div className="graph-rels-head">
            <h4>Dónde mirar</h4>
            <p className="muted">{picked ? picked.name : `${rows.length} lugares`}</p>
            <input
              type="search"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Buscar Texas, Chiapas…"
              aria-label="Buscar lugar"
            />
            {picked ? (
              <button type="button" className="ghost" onClick={() => setPicked(null)}>
                Ver todos
              </button>
            ) : null}
          </div>
          <div className="graph-rels-body">
            {rows.length ? (
              <table>
                <thead>
                  <tr>
                    <th>Lugar</th>
                    <th>Notas</th>
                    <th>De qué</th>
                    <th>Desde</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((p) => (
                    <tr
                      key={pointKey(p)}
                      className={picked && pointKey(picked) === pointKey(p) ? "on" : ""}
                      onClick={() => setPicked(p)}
                    >
                      <td>
                        <strong>{p.name}</strong>
                        <em>
                          {grainLabel(p)}
                          {p.risk_mean != null ? ` · riesgo ${riskHint(p.risk_mean)}` : ""}
                        </em>
                      </td>
                      <td className="rel">{p.count}</td>
                      <td>{diseaseLabel(p)}</td>
                      <td className="rel">{p.first_seen || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="muted">Ningún lugar coincide.</p>
            )}
          </div>
        </aside>
      </div>
      {picked ? (
        <div className="graph-pick map-pick">
          <div>
            <strong>{picked.name}</strong>
            <em>
              {" "}
              · {picked.count} notas · {diseaseLabel(picked)}
              {picked.risk_mean != null ? ` · riesgo ${riskHint(picked.risk_mean)}` : ""}
              {picked.first_seen ? ` · desde ${picked.first_seen}` : ""}
            </em>
            {picked.articles?.length ? (
              <ul className="map-pick-arts">
                {picked.articles.slice(0, 3).map((a) => (
                  <li key={a.content_id}>{a.title}</li>
                ))}
              </ul>
            ) : null}
          </div>
          <button type="button" className="run" onClick={() => onOpenSala(picked)}>
            Ver en la sala
          </button>
        </div>
      ) : (
        <p className="muted">Pulsa un punto o una fila. Luego “Ver en la sala”.</p>
      )}
      {lostNotes ? (
        <p className="muted unlocated-line">
          Sin ubicar ({lostNotes}): {unlocated.map((u) => `${u.name} ${u.count}`).join(" · ")}
        </p>
      ) : null}
    </section>
  );
}
