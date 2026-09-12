import { FormEvent, useState } from "react";
import BrandMark from "./components/BrandMark";
import { useLicense } from "./license";

const REASON: Record<string, string> = {
  correo: "Ese correo no sirve.",
  clave_corta: "La contraseña pide 8 caracteres.",
  dispositivo: "No se pudo identificar este equipo.",
  existe: "Esa cuenta ya está creada. Entra.",
  cupo: "Esta licencia ya está en 3 equipos. Quita uno desde un equipo activo.",
  credenciales: "Correo o contraseña no coinciden.",
  licencia: "Esa clave TNB1 no sirve o ya caducó.",
  formato: "La clave TNB1 no tiene el formato.",
  firma: "La clave TNB1 no es válida.",
  caducada: "La licencia caducó.",
};

export default function Login() {
  const { login, register } = useLicense();
  const [mode, setMode] = useState<"entrar" | "crear">("entrar");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [key, setKey] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  function takeKey(raw: string) {
    const compact = raw.replace(/\u200b/g, "").replace(/\s+/g, "");
    const found = compact.match(/TNB1\.[A-Za-z0-9_-]+\.[0-9a-fA-F]{8,64}/);
    return found ? found[0] : raw.trim();
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErr("");
    try {
      if (mode === "crear") {
        await register(email.trim(), password, takeKey(key));
      } else {
        await login(email.trim(), password, takeKey(key));
      }
    } catch (ex) {
      const msg = ex instanceof Error ? ex.message : "";
      const code = msg.split(/\s+/).pop() || msg;
      setErr(REASON[code] || (mode === "crear" ? "No se pudo crear la cuenta." : "No se pudo entrar."));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="gate login-gate">
      <div className="gate-sky" aria-hidden="true" />
      <div className="login-card">
        <div className="brand-block">
          <BrandMark />
          <div>
            <p className="kicker">The NewsBreakers</p>
            <h1>{mode === "crear" ? "Crear cuenta" : "Iniciar sesión"}</h1>
            <p className="muted header-sub">
              {mode === "crear"
                ? "Correo, contraseña y, si tienes, la clave TNB1. Máximo 3 equipos por licencia."
                : "Entra con tu cuenta. Sin licencia ves 4 notas. Con TNB1 se abre la sala."}
            </p>
          </div>
        </div>
        <form className="login-form" onSubmit={onSubmit}>
          <label>
            Correo
            <input
              type="email"
              autoComplete="username"
              value={email}
              onChange={(ev) => setEmail(ev.target.value)}
              required
            />
          </label>
          <label>
            Contraseña
            <input
              type="password"
              autoComplete={mode === "crear" ? "new-password" : "current-password"}
              value={password}
              onChange={(ev) => setPassword(ev.target.value)}
              minLength={8}
              required
            />
          </label>
          <label>
            Clave TNB1 {mode === "entrar" ? "(si aún no está ligada)" : "(opcional)"}
            <textarea
              value={key}
              onChange={(ev) => setKey(takeKey(ev.target.value))}
              placeholder="TNB1.…"
              rows={2}
              spellCheck={false}
              autoComplete="off"
            />
          </label>
          <button type="submit" className="gate-go" disabled={busy || email.trim().length < 3 || password.length < 8}>
            {busy ? "Abriendo…" : mode === "crear" ? "Crear e entrar" : "Entrar"}
          </button>
          {err ? <p className="license-err">{err}</p> : null}
        </form>
        <p className="login-switch">
          {mode === "entrar" ? (
            <button type="button" className="linkish" onClick={() => setMode("crear")}>
              Crear cuenta
            </button>
          ) : (
            <button type="button" className="linkish" onClick={() => setMode("entrar")}>
              Ya tengo cuenta
            </button>
          )}
        </p>
      </div>
    </div>
  );
}
