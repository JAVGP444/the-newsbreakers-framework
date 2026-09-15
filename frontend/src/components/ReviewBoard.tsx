import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, verdictClass, type AlertRow } from "../api";
import { flowText, verdictLabel } from "../display";
import { articleHref } from "../safeUrl";
import { HitlButtons } from "./HitlButtons";

export default function ReviewBoard({
  alerts,
  pendingHint = 0,
  loading = false,
  onDone,
}: {
  alerts: AlertRow[];
  pendingHint?: number;
  loading?: boolean;
  onDone: () => Promise<void>;
}) {
  const [currentId, setCurrentId] = useState(alerts[0]?.alert_id || "");
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState("");
  const [edit, setEdit] = useState(false);
  const [reason, setReason] = useState("");

  useEffect(() => {
    if (!alerts.some((a) => a.alert_id === currentId)) {
      setCurrentId(alerts[0]?.alert_id || "");
      setEdit(false);
      setReason("");
    }
  }, [alerts, currentId]);

  const current = alerts.find((a) => a.alert_id === currentId) || alerts[0] || null;

  async function act(label: "validado" | "descartado" | "modificado", why = "") {
    if (!current) return;
    if (label === "modificado" && !why.trim()) {
      setEdit(true);
      return;
    }
    setBusy(true);
    setNote("");
    try {
      await api.review(current.alert_id, label, why);
      setNote(
        label === "validado" ? "Quedó como correcto." : label === "descartado" ? "Quedó fuera de la cola." : "Quedó corregido."
      );
      setEdit(false);
      setReason("");
      await onDone();
    } catch (e) {
      setNote(e instanceof Error ? e.message : "No se pudo guardar. Inténtalo de nuevo.");
    } finally {
      setBusy(false);
    }
  }

  if (!alerts.length) {
    const waiting = loading || pendingHint > 0;
    return (
      <section className="viz">
        <h3>{waiting ? "Cargando la cola" : "Nada en cola"}</h3>
        <p className="muted">
          {waiting
            ? pendingHint > 0
              ? `Hay ${pendingHint} pendiente${pendingHint === 1 ? "" : "s"}. Un momento, se está armando la cola.`
              : "Un momento, se está armando la cola."
            : "Cuando una nota pida ojo humano, aparece aquí. Una a una: afirmación, evidencia, decisión."}
        </p>
      </section>
    );
  }

  return (
    <div className="review-board">
      <aside className="review-rail" aria-label="Cola de revisión">
        <p className="muted">
          {alerts.length} pendiente{alerts.length === 1 ? "" : "s"}
        </p>
        {alerts.map((a, i) => (
          <button
            key={a.alert_id}
            type="button"
            className={a.alert_id === current?.alert_id ? "on" : ""}
            onClick={() => {
              setCurrentId(a.alert_id);
              setEdit(false);
              setReason("");
              setNote("");
            }}
          >
            <span className="review-rail-n">{i + 1}</span>
            <span>
              <strong>{a.title || a.content_id}</strong>
              <em>
                {verdictLabel(a.verdict)}
                {a.risk_score != null ? ` · riesgo ${a.risk_score}` : ""}
              </em>
            </span>
          </button>
        ))}
      </aside>

      {current ? (
        <article className="review-focus">
          <p className="review-task">Lee la afirmación y la evidencia. Luego di si el análisis se sostiene.</p>
          <h3>
            <Link to={articleHref(current.content_id)}>{current.title || current.content_id}</Link>
          </h3>
          <p className="art-meta">
            <span className={`pill ${verdictClass(current.verdict)}`}>{verdictLabel(current.verdict)}</span>
            {current.risk_score != null ? <span>Riesgo {current.risk_score}</span> : null}
          </p>
          {note ? <p className="banner">{note}</p> : null}

          <div className="review-step">
            <h4>1. Qué afirma la nota</h4>
            {current.primary_claim ? <p>{flowText(current.primary_claim)}</p> : <p className="muted">Esta nota no trajo una frase contrastable.</p>}
            {current.contrast?.facts?.length ? (
              <p className="review-facts">
                {current.contrast.facts.map((f) => (
                  <span key={f} className="pill mid">
                    {f}
                  </span>
                ))}
              </p>
            ) : null}
          </div>
          <div className="review-step">
            <h4>2. Con qué se contrastó</h4>
            {current.contrast?.status === "hit" && current.contrast.snippet ? (
              <>
                <p className="art-meta">
                  <span className={`pill ${verdictClass(current.contrast.stance)}`}>
                    {current.contrast.stance === "Contradicted" ? "Contradice la nota" : "Afirma los mismos hechos"}
                  </span>
                </p>
                <p>{flowText(current.contrast.snippet)}</p>
                {current.contrast.url ? (
                  <p className="review-source">
                    <a href={current.contrast.url} target="_blank" rel="noreferrer">
                      {current.contrast.title || current.contrast.url}
                    </a>
                  </p>
                ) : null}
              </>
            ) : current.contrast?.status === "partial" && current.contrast.snippet ? (
              <>
                <p className="art-meta">
                  <span className="pill warn">Coincide en parte</span>
                </p>
                <p>{flowText(current.contrast.snippet)}</p>
                {current.contrast.why ? <p className="muted">{current.contrast.why}</p> : null}
                {current.contrast.url ? (
                  <p className="review-source">
                    <a href={current.contrast.url} target="_blank" rel="noreferrer">
                      {current.contrast.title || current.contrast.url}
                    </a>
                  </p>
                ) : null}
              </>
            ) : (
              <p className="muted">
                {current.contrast?.why ||
                  "No hay boletín oficial de estos hechos. Si no hay con qué contrastar, no valides."}
              </p>
            )}
            {current.contrast?.peers?.length ? (
              <ul className="review-peers">
                {current.contrast.peers.map((p) => (
                  <li key={p.content_id || p.title}>{p.title}</li>
                ))}
              </ul>
            ) : null}
          </div>
          <div className="review-step">
            <h4>3. Tu decisión</h4>
            <HitlButtons
              busy={busy}
              onAct={(label) => act(label)}
              labels={{ validado: "Se sostiene", descartado: "No aplica", modificado: "Corregir" }}
            />
            {edit ? (
              <label className="hitl-reason">
                Qué hay que corregir
                <textarea value={reason} onChange={(e) => setReason(e.target.value)} rows={3} />
                <button type="button" className="run" disabled={!reason.trim() || busy} onClick={() => act("modificado", reason)}>
                  Guardar corrección
                </button>
              </label>
            ) : null}
          </div>
        </article>
      ) : null}
    </div>
  );
}
