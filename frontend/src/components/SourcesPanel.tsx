import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { api, type SourceRow } from "../api";
import { filtersToSearch, type ObservatoryFilters } from "../filters";
import { useLocale } from "../locale";

export default function SourcesPanel({
  sources,
  filters,
  onSaved,
}: {
  sources: SourceRow[];
  filters: ObservatoryFilters;
  onSaved: () => Promise<void> | void;
}) {
  const { t } = useLocale();
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
      setNote(t("sources.added"));
      await onSaved();
    } catch (err) {
      setNote(err instanceof Error ? err.message : t("sources.addFail"));
    }
  }

  async function toggle(s: SourceRow) {
    await api.saveSource({ source_id: s.source_id, active: !s.active });
    await onSaved();
  }

  return (
    <section className="viz">
      <h3>{t("sources.title")}</h3>
      <p className="muted">
        {t("sources.lead", { n: sources.length, used: used.length })}
      </p>
      <form className="filter-row" onSubmit={add}>
        <label>
          {t("sources.name")}
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder="WOAH / WAHIS" />
        </label>
        <label>
          {t("sources.url")}
          <input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://" />
        </label>
        <label>
          {t("sources.type")}
          <select value={type} onChange={(e) => setType(e.target.value)}>
            <option value="oficial">{t("type.oficial")}</option>
            <option value="cientifica">{t("type.cientifica")}</option>
            <option value="medio">{t("type.medio")}</option>
            <option value="foro">{t("type.foro")}</option>
            <option value="normativa">{t("type.normativa")}</option>
          </select>
        </label>
        <button type="submit" className="run">
          {t("sources.add")}
        </button>
      </form>
      {note ? <p className="muted">{note}</p> : null}
      {!sources.length ? <p className="muted">{t("sources.empty")}</p> : null}
      <div className="source-table-wrap">
        <table className="source-table">
          <thead>
            <tr>
              <th>{t("sources.col.source")}</th>
              <th>{t("sources.col.type")}</th>
              <th>{t("sources.col.country")}</th>
              <th>{t("sources.col.method")}</th>
              <th>{t("sources.col.last")}</th>
              <th>{t("sources.col.docs")}</th>
              <th>{t("sources.col.used")}</th>
              <th>{t("sources.col.active")}</th>
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
                  <td>{s.last_checked || t("sources.never")}</td>
                  <td>{s.article_count ?? 0}</td>
                  <td>{s.evidence_uses ?? 0}</td>
                  <td>
                    <button type="button" className={`chip source-health ${status}`} onClick={() => toggle(s)}>
                      {s.active === 0 || s.active === false ? t("sources.off") : t("sources.on")}
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
          {open ? t("common.less") : t("common.more")}
        </button>
      ) : null}
    </section>
  );
}
