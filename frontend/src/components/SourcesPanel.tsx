import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { api, type SourceRow } from "../api";
import { filtersToSearch, type ObservatoryFilters } from "../filters";

export default function SourcesPanel({
  sources,
  filters,
  onSaved,
}: {
  sources: SourceRow[];
  filters: ObservatoryFilters;
  onSaved: () => Promise<void> | void;
}) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const [type, setType] = useState("medio");
  const [note, setNote] = useState("");

  const used = sources.filter((s) => (s.evidence_uses || 0) > 0);
  const preview = 16;
  const extra = sources.length > preview;
  const rows = open || !extra ? sources : sources.slice(0, preview);

  async function add(e: FormEvent) {
    e.preventDefault();
    try {
      await api.saveSource({ name, rss_url: url, base_url: url, type, active: true }, true);
      setName("");
      setUrl("");
      setNote("Fuente agregada. Disponible para ingesta; el contraste la marcará como usada cuando participe.");
      await onSaved();
    } catch (err) {
      setNote(err instanceof Error ? err.message : "No se pudo agregar.");
    }
  }

  async function toggle(s: SourceRow) {
    await api.saveSource({ source_id: s.source_id, active: !s.active });
    await onSaved();
  }

  return (
    <section className="viz">
      <h3>Fuentes</h3>
      <p className="muted">
        Disponibles: {sources.length}. Usadas en contraste: {used.length}. Tener OMS en el catálogo no cuenta como haberla
        consultado.
      </p>
      <form className="filter-row" onSubmit={add}>
        <label>
          Nombre
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder="WOAH / WAHIS" />
        </label>
        <label>
          URL / RSS
          <input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://" />
        </label>
        <label>
          Tipo
          <select value={type} onChange={(e) => setType(e.target.value)}>
            <option value="oficial">Oficial</option>
            <option value="cientifica">Científica</option>
            <option value="medio">Medio</option>
            <option value="foro">Foro</option>
            <option value="normativa">Normativa</option>
          </select>
        </label>
        <button type="submit" className="run">
          Agregar
        </button>
      </form>
      {note ? <p className="muted">{note}</p> : null}
      {!sources.length ? <p className="muted">Todavía no hay fuentes en el catálogo.</p> : null}
      <div className="source-table-wrap">
        <table className="source-table">
          <thead>
            <tr>
              <th>Fuente</th>
              <th>Tipo</th>
              <th>País</th>
              <th>Método</th>
              <th>Última captura</th>
              <th>Documentos</th>
              <th>Usada en contraste</th>
              <th>Activa</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((s) => {
              const status = s.status || (s.last_error ? "error" : "ok");
              return (
                <tr key={s.source_id}>
                  <td>
                    <Link to={{ pathname: "/", search: filtersToSearch({ ...filters, source: s.source_id, page: 1 }) }}>
                      {s.name || s.source_id}
                    </Link>
                    <div className="muted">{s.domain}</div>
                  </td>
                  <td>{s.type || "—"}</td>
                  <td>{s.country || "—"}</td>
                  <td>{s.access_method || "—"}</td>
                  <td>{s.last_checked || "Nunca"}</td>
                  <td>{s.article_count ?? 0}</td>
                  <td>{s.evidence_uses ?? 0}</td>
                  <td>
                    <button type="button" className={`chip source-health ${status}`} onClick={() => toggle(s)}>
                      {s.active === 0 || s.active === false ? "Inactiva" : "Activa"}
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {extra ? (
        <button type="button" className="leer-mas-btn" onClick={() => setOpen((v) => !v)}>
          {open ? "Leer menos" : "Leer más"}
        </button>
      ) : null}
    </section>
  );
}
