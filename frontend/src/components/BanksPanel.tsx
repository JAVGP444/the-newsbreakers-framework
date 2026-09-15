import { useEffect, useState, type FormEvent } from "react";
import { api, type KeywordTerm } from "../api";

export default function BanksPanel() {
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
      .catch(() => setErr("No se pudo cargar el banco."));

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
      <h3>Banco de términos</h3>
      <p className="ficha-lead">{principle || "peso ≠ malicia. El término es una señal, no un veredicto."}</p>
      {err ? <p className="banner err">{err}</p> : null}
      <form className="filter-row" onSubmit={add}>
        <label>
          Término
          <input value={term} onChange={(e) => setTerm(e.target.value)} placeholder="ocultar" />
        </label>
        <label>
          Categoría
          <select value={category} onChange={(e) => setCategory(e.target.value)}>
            {cats.length ? cats.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            )) : <option value="ocultamiento">ocultamiento</option>}
          </select>
        </label>
        <label>
          Peso (1–5)
          <input type="number" min={1} max={5} value={weight} onChange={(e) => setWeight(Number(e.target.value))} />
        </label>
        <button type="submit" className="run">
          Agregar
        </button>
      </form>
      <div className="source-table-wrap">
        <table className="source-table">
          <thead>
            <tr>
              <th>Término</th>
              <th>Categoría</th>
              <th>Peso</th>
              <th>Activo</th>
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
                    {row.active ? "Sí" : "No"}
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
