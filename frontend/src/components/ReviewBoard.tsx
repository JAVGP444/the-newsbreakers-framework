import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, verdictClass, type AlertRow } from "../api";
import { flowText, verdictLabel } from "../display";
import { useLocale } from "../locale";
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
  const { t, lang } = useLocale();
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
      setNote(label === "validado" ? t("review.ok") : label === "descartado" ? t("review.drop") : t("review.edit"));
      setEdit(false);
      setReason("");
      await onDone();
    } catch (e) {
      setNote(e instanceof Error ? e.message : t("common.saveFail"));
    } finally {
      setBusy(false);
    }
  }

  if (!alerts.length) {
    const waiting = loading || pendingHint > 0;
    return (
      <section className="viz">
        <h3>{waiting ? t("review.loading") : t("review.empty")}</h3>
        <p className="muted">
          {waiting
            ? pendingHint > 0
              ? t("review.waitingN", {
                  n: pendingHint,
                  s: pendingHint === 1 ? "" : "s",
                  be: pendingHint === 1 ? "is" : "are",
                })
              : t("review.waiting")
            : t("review.idle")}
        </p>
      </section>
    );
  }

  return (
    <div className="review-board">
      <aside className="review-rail" aria-label={t("review.aria")}>
        <p className="muted">{t("review.pending", { n: alerts.length, s: alerts.length === 1 ? "" : "s" })}</p>
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
                {verdictLabel(a.verdict, lang)}
                {a.risk_score != null ? ` · ${t("review.riskN", { n: a.risk_score })}` : ""}
              </em>
            </span>
          </button>
        ))}
      </aside>

      {current ? (
        <article className="review-focus">
          <p className="review-task">{t("review.task")}</p>
          <h3>
            <Link to={articleHref(current.content_id)}>{current.title || current.content_id}</Link>
          </h3>
          <p className="art-meta">
            <span className={`pill ${verdictClass(current.verdict)}`}>{verdictLabel(current.verdict, lang)}</span>
            {current.risk_score != null ? <span>{t("risk.n", { n: current.risk_score })}</span> : null}
          </p>
          {note ? <p className="banner">{note}</p> : null}

          <div className="review-step">
            <h4>{t("review.claim")}</h4>
            {current.primary_claim ? <p>{flowText(current.primary_claim)}</p> : <p className="muted">{t("review.noClaim")}</p>}
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
            <h4>{t("review.contrast")}</h4>
            {current.contrast?.status === "hit" && current.contrast.snippet ? (
              <>
                <p className="art-meta">
                  <span className={`pill ${verdictClass(current.contrast.stance)}`}>
                    {current.contrast.stance === "Contradicted" ? t("review.contradicts") : t("review.sameFacts")}
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
                  <span className="pill warn">{t("review.partial")}</span>
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
              <p className="muted">{current.contrast?.why || t("review.noBulletin")}</p>
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
            <h4>{t("review.decision")}</h4>
            <HitlButtons busy={busy} onAct={(label) => act(label)} />
            {edit ? (
              <label className="hitl-reason">
                {t("review.fixWhat")}
                <textarea value={reason} onChange={(e) => setReason(e.target.value)} rows={3} />
                <button type="button" className="run" disabled={!reason.trim() || busy} onClick={() => act("modificado", reason)}>
                  {t("review.saveFix")}
                </button>
              </label>
            ) : null}
          </div>
        </article>
      ) : null}
    </div>
  );
}
