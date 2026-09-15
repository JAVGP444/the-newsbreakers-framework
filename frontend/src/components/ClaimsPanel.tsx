import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type Claim } from "../api";

export default function ClaimsPanel() {
  const [rows, setRows] = useState<Claim[]>([]);
  const [q, setQ] = useState("");
  const [err, setErr] = useState("");

  useEffect(() => {
    const params = q ? `q=${encodeURIComponent(q)}` : "";
    api
      .claims(params)
      .then((r) => {
        setRows(r.claims || []);
        setErr("");
      })
      .catch(() => setErr("No se pudieron cargar las afirmaciones."));
  }, [q]);

  return (
    <section className="viz">
      <h3>Afirmaciones</h3>
      <p className="muted">Cada afirmación se contrasta por separado. La modalidad evita tratar una pregunta como un hecho.</p>
      {err ? <p className="banner err">{err}</p> : null}
      <label className="search-box">
        <span className="sr-only">Buscar afirmación</span>
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Buscar afirmación…" />
      </label>
      <div className="source-table-wrap">
        <table className="source-table">
          <thead>
            <tr>
              <th>Afirmación</th>
              <th>Sujeto</th>
              <th>Acción</th>
              <th>Modalidad</th>
              <th>Resultado</th>
            </tr>
          </thead>
          <tbody>
            {rows.slice(0, 80).map((c) => (
              <tr key={c.claim_id}>
                <td>
                  {c.content_id ? (
                    <Link to={`/article/${encodeURIComponent(c.content_id)}`}>{c.text}</Link>
                  ) : (
                    c.text
                  )}
                </td>
                <td>{c.subject || "—"}</td>
                <td>{c.predicate || "—"}</td>
                <td>{c.modality || "—"}</td>
                <td>{c.nli_label || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
