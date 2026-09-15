import { useCallback, useState } from "react";
import { useLocale } from "../locale";

const STORAGE_KEY = "tnb.verdictLegendOpen";

const STATE_KEYS = [
  { id: "ok", label: "verdict.respaldado", why: "verdict.respaldadoWhy", tone: "ok" },
  { id: "mid", label: "verdict.insuficiente", why: "verdict.insuficienteWhy", tone: "mid" },
  { id: "warn", label: "verdict.enganoso", why: "verdict.enganosoWhy", tone: "warn" },
  { id: "bad", label: "verdict.contradicho", why: "verdict.contradichoWhy", tone: "bad" },
  { id: "human", label: "verdict.humana", why: "verdict.humanaWhy", tone: "human" },
] as const;

function readOpen(): boolean {
  try {
    return localStorage.getItem(STORAGE_KEY) === "1";
  } catch {
    return false;
  }
}

export default function VerdictLegend() {
  const { t } = useLocale();
  const [open, setOpen] = useState(readOpen);

  const toggle = useCallback(() => {
    setOpen((prev) => {
      const next = !prev;
      try {
        localStorage.setItem(STORAGE_KEY, next ? "1" : "0");
      } catch {
        /* ignore quota / private mode */
      }
      return next;
    });
  }, []);

  return (
    <div className={`verdict-legend${open ? " open" : ""}`}>
      <div className="verdict-legend-bar">
        {STATE_KEYS.map((s) => (
          <span key={s.id} className={`legend-chip ${s.tone}`} title={t(s.why)}>
            {t(s.label)}
          </span>
        ))}
        <button
          type="button"
          className="verdict-legend-toggle"
          aria-expanded={open}
          aria-controls="verdict-legend-list"
          onClick={toggle}
        >
          {open ? t("legend.hide") : t("legend.show")}
        </button>
      </div>
      {open ? (
        <ul id="verdict-legend-list" className="verdict-legend-list">
          {STATE_KEYS.map((s) => (
            <li key={s.id} className="verdict-legend-item">
              <span className={`pill ${s.tone}`}>{t(s.label)}</span>
              <span>{t(s.why)}</span>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
