import { useEffect, useState, type FormEvent } from "react";
import { api, type KeywordTerm } from "../api";
import { useLocale } from "../locale";

export default function BanksPanel() {
  const { t } = useLocale();
  const [terms, setTerms] = useState<KeywordTerm[]>([]);
  const [principle, setPrinciple] = useState("");
  const [err, setErr] = useState("");
  const [term, setTerm] = useState("");
  const [category, setCategory] = useState("ocultamiento");
  const [weight, setWeight] = useState(3);

  const load = () =>
    api
      .bankTerms()
      .then((r) => {
        setTerms(r.terms || []);
        setPrinciple(r.principle || "");
        setErr("");
      })
      .catch(() => setErr(t("banks.fail")));

  useEffect(() => {
    load();
  }, []);

  async function add(e: FormEvent) {
    e.preventDefault();
    if (!term.trim()) return;
    await api.saveTerm({ term: term.trim(), category, weight, active: 1 });
    setTerm("");
    await load();
  }

  async function toggle(row: KeywordTerm) {
    await api.saveTerm({ ...row, active: row.active ? 0 : 1 });
    await load();
  }

  const cats = Array.from(new Set(terms.map((t) => t.category)));

  return (
    <section className="viz">
      <h3>{t("banks.title")}</h3>
      <p className="ficha-lead">{principle || t("banks.lead")}</p>
      {err ? <p className="banner err">{err}</p> : null}
      <form className="filter-row" onSubmit={add}>
        <label>
          {t("banks.term")}
          <input value={term} onChange={(e) => setTerm(e.target.value)} placeholder="ocultar" />
        </label>
        <label>
          {t("banks.category")}
          <select value={category} onChange={(e) => setCategory(e.target.value)}>
            {cats.length ? cats.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            )) : <option value="ocultamiento">ocultamiento</option>}
          </select>
        </label>
        <label>
          {t("banks.weight")}
          <input type="number" min={1} max={5} value={weight} onChange={(e) => setWeight(Number(e.target.value))} />
        </label>
        <button type="submit" className="run">
          {t("banks.add")}
        </button>
      </form>
      <div className="source-table-wrap">
        <table className="source-table">
          <thead>
            <tr>
              <th>{t("banks.term")}</th>
              <th>{t("banks.category")}</th>
              <th>{t("nar.col.force")}</th>
              <th>{t("banks.active")}</th>
            </tr>
          </thead>
          <tbody>
            {terms.map((row) => (
              <tr key={row.term_id}>
                <td>{row.term}</td>
                <td>{row.label || row.category}</td>
                <td>{row.weight}</td>
                <td>
                  <button type="button" className="chip" onClick={() => toggle(row)}>
                    {row.active ? t("banks.on") : t("banks.off")}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
