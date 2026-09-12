import { useCallback, useState } from "react";

const STORAGE_KEY = "tnb.verdictLegendOpen";

const STATES = [
  {
    label: "Respaldado",
    tone: "ok",
    text: "Hay evidencia oficial o científica alineada con la afirmación.",
  },
  {
    label: "Insuficiente",
    tone: "mid",
    text: "No hay evidencia bastante para concluir.",
  },
  {
    label: "Posiblemente engañoso",
    tone: "warn",
    text: "Hay inconsistencias relevantes en la evidencia.",
  },
  {
    label: "Contradicho",
    tone: "bad",
    text: "La evidencia oficial contradice la afirmación.",
  },
  {
    label: "Revisión humana",
    tone: "human",
    text: "Baja confianza: un analista debe validar.",
  },
] as const;

function readOpen(): boolean {
  try {
    return localStorage.getItem(STORAGE_KEY) === "1";
  } catch {
    return false;
  }
}

export default function VerdictLegend() {
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
        {STATES.map((s) => (
          <span key={s.label} className={`legend-chip ${s.tone}`} title={s.text}>
            {s.label}
          </span>
        ))}
        <button
          type="button"
          className="verdict-legend-toggle"
          aria-expanded={open}
          aria-controls="verdict-legend-list"
          onClick={toggle}
        >
          {open ? "Ocultar" : "Qué es cada uno"}
        </button>
      </div>
      {open ? (
        <ul id="verdict-legend-list" className="verdict-legend-list">
          {STATES.map((s) => (
            <li key={s.label} className="verdict-legend-item">
              <span className={`pill ${s.tone}`}>{s.label}</span>
              <span>{s.text}</span>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
