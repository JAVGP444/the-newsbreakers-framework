import { FormEvent, useEffect, useState } from "react";
import { api, type LicenseInfo } from "../api";
import { useLicense } from "../license";

const FREE = [
  "Sala, gráficos, CNN y traductor con lo ya guardado",
  "Un ciclo de prueba: 8 fuentes, GDELT corto",
];
const PAID = [
  "Minería 24/7 de toda la watchlist (~250 fuentes)",
  "GDELT y RSS sin recortar",
  "OpenAI/Anthropic en las fichas (tu API key)",
  "OCR Document Intelligence si tienes el Studio",
];

export default function LicenseBar() {
  const { account, logout, refresh, licensed, info: ctxInfo } = useLicense();
  const [info, setInfo] = useState<LicenseInfo | null>(null);
  const [key, setKey] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    api
      .license()
      .then(setInfo)
      .catch(() => setInfo(null));
  }, []);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErr("");
    try {
      const next = await api.activateLicense(key.trim());
      setInfo(next);
      setKey("");
      await refresh();
    } catch {
      setErr("Clave no válida o caducada.");
    } finally {
      setBusy(false);
    }
  }

  const shown = ctxInfo || info;
  const feats = (shown?.features || []).join(", ") || "—";
  const paidRaw = shown?.paid || [];
  const paid = paidRaw.some((line) => line.length > 12) ? paidRaw : PAID;
  const freeRaw = shown?.free || [];
  const free = freeRaw.some((line) => line.length > 12) ? freeRaw : FREE;

  return (
    <div className={licensed ? "license-bar on" : "license-bar"} data-license={licensed ? "on" : "off"}>
      {licensed ? (
        <p className="license-copy">
          {account?.email ? `${account.email} · ` : ""}
          Licencia activa · {feats} · caduca {shown?.exp || "—"}
          {shown?.who ? ` · ${shown.who}` : ""}
          {account?.device_max ? ` · ${account.device_n || 0}/${account.device_max} equipos` : ""}
          <button type="button" className="linkish" onClick={() => void logout()}>
            Cerrar sesión
          </button>
        </p>
      ) : (
        <form className="license-form" onSubmit={onSubmit}>
          <div className="license-copy">
            <p>
              Evaluación. Ves el observatorio. Un ciclo solo toca {shown?.caps?.max_sources ?? 8} fuentes. Para eso
              pagarías:
            </p>
            <ul className="license-list">
              {paid.map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
            <p className="license-free">Sin clave te queda: {free.join(". ")}.</p>
            <button type="button" className="linkish" onClick={() => void logout()}>
              Cerrar sesión
            </button>
          </div>
          <input
            value={key}
            onChange={(ev) => setKey(ev.target.value)}
            placeholder="Pega tu clave TNB1…"
            aria-label="Clave de licencia"
            autoComplete="off"
            spellCheck={false}
          />
          <button type="submit" className="run" disabled={busy || key.trim().length < 8}>
            {busy ? "Activando…" : "Activar"}
          </button>
          {err ? <span className="license-err">{err}</span> : null}
        </form>
      )}
    </div>
  );
}
