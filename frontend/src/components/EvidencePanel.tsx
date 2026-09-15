import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type EvidenceRow } from "../api";

type Row = EvidenceRow & { claim_text?: string; content_id?: string; official?: boolean };

export default function EvidencePanel() {
  const [rows, setRows] = useState<Row[]>([]);
  const [err, setErr] = useState("");

  useEffect(() => {
    api
      .evidence()
      .then((r) => {
        setRows((r.evidence || []) as Row[]);
        setErr("");
      })
      .catch(() => setErr("No se pudo cargar la evidencia."));
  }, []);

  return (
    <section className="viz">
      <h3>Evidencia</h3>
      <p className="muted">
        Resultado → fragmento → fuente. El sistema no inventa evidencia. Distingue fuentes disponibles de fuentes usadas.
      </p>
      {err ? <p className="banner err">{err}</p> : null}
      <div className="source-table-wrap">
        <table className="source-table">
          <thead>
            <tr>
              <th>Afirmación</th>
              <th>Fuente</th>
              <th>Tipo</th>
              <th>Resultado</th>
            </tr>
          </thead>
          <tbody>
            {rows.slice(0, 80).map((e) => (
              <tr key={e.evidence_id}>
                <td>
                  {e.content_id ? (
                    <Link to={`/article/${encodeURIComponent(e.content_id)}`}>{e.claim_text || e.snippet || e.claim_id}</Link>
                  ) : (
                    e.claim_text || e.snippet || e.claim_id
                  )}
                </td>
                <td>
                  {e.url ? (
                    <a href={e.url} target="_blank" rel="noreferrer">
                      {e.url.replace(/^https?:\/\//, "").slice(0, 48)}
                    </a>
                  ) : (
                    "—"
                  )}
                </td>
                <td>{e.source_tier || "—"}</td>
                <td>{e.stance || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
