import { FormEvent, useEffect, useState } from "react";
import { api, type Article, type GeoRow } from "./api";
import ArticleCard from "./components/ArticleCard";
import BrandMark from "./components/BrandMark";
import MapView from "./components/MapView";
import { Sparkline } from "./components/Sparkline";
import { ensureGeoPoints } from "./geoCentroids";
import { useLicense } from "./license";

const LOCKED_NAV = ["Sala", "Revisión", "Mapa", "Gráficas", "Grafo", "CNN", "Fuentes"];

export default function Preview() {
  const { activate, logout, account } = useLicense();
  const [articles, setArticles] = useState<Article[]>([]);
  const [geo, setGeo] = useState<GeoRow[]>([]);
  const [key, setKey] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  function takeKey(raw: string) {
    const compact = raw.replace(/\u200b/g, "").replace(/\s+/g, "");
    const found = compact.match(/TNB1\.[A-Za-z0-9_-]+\.[0-9a-fA-F]{8,64}/);
    return found ? found[0] : raw.trim();
  }

  useEffect(() => {
    let cancelled = false;
    Promise.all([api.articles("", 1, 4), api.geo("")])
      .then(([arts, g]) => {
        if (cancelled) return;
        const rows = (arts.articles || []).slice(0, 4);
        setArticles(rows);
        const points = ensureGeoPoints(g.points?.length ? g.points : (g.countries || []).filter((c) => !c.unlocated), rows);
        setGeo(
          points.map((p) => ({
            ...p,
            name: "Censurado",
            articles: [],
          }))
        );
      })
      .catch(() => {
        if (!cancelled) setArticles([]);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErr("");
    try {
      await activate(takeKey(key));
    } catch {
      setErr("Esa clave no sirve o ya caducó.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="gate">
      <div className="gate-sky" aria-hidden="true" />
      <div className="shell observatory">
        <header className="site-header">
          <div className="site-header-inner">
            <div className="brand-block">
              <BrandMark />
              <div>
                <p className="kicker">The NewsBreakers</p>
                <h1>Sala de vigilancia</h1>
                <p className="muted header-sub">Gusano barrenador · gripe aviar · PPC. El resto de la sala pide clave.</p>
                {account?.email ? <p className="muted">{account.email}</p> : null}
              </div>
            </div>
            <form className="gate-pass" onSubmit={onSubmit}>
              <div className="gate-pass-copy">
                <p className="gate-key-kicker">Licencia</p>
                <p>Pega el código TNB1. Se abre sala, minería, CNN, mapa y grafo.</p>
              </div>
              <label className="sr-only" htmlFor="tnb-license">
                Clave
              </label>
              <textarea
                id="tnb-license"
                value={key}
                onChange={(ev) => setKey(takeKey(ev.target.value))}
                onPaste={(ev) => {
                  const text = ev.clipboardData.getData("text");
                  if (!text) return;
                  ev.preventDefault();
                  setKey(takeKey(text));
                }}
                placeholder="Pega aquí TNB1.…"
                autoComplete="off"
                spellCheck={false}
                rows={2}
              />
              <button
                type="button"
                className="gate-paste"
                disabled={busy}
                onClick={async () => {
                  setErr("");
                  try {
                    setKey(takeKey(await navigator.clipboard.readText()));
                  } catch {
                    setErr("Cmd+V o menú Editar → Pegar.");
                  }
                }}
              >
                Pegar
              </button>
              <button type="submit" className="gate-go" disabled={busy || takeKey(key).length < 8}>
                {busy ? "Abriendo…" : "Activar"}
              </button>
              {err ? <p className="license-err">{err}</p> : null}
              <button type="button" className="linkish" onClick={() => void logout()}>
                Cerrar sesión
              </button>
            </form>
          </div>
          <nav className="site-nav" aria-label="Secciones del observatorio">
            {LOCKED_NAV.map((label, i) => (
              <span key={label} className={i === 0 ? "nav-link on" : "nav-link is-lock"}>
                {label}
              </span>
            ))}
          </nav>
        </header>

        <p className="banner mine-banner">Minería detenida · archivo censurado · ciclo y CNN cerrados</p>

        <section className="kpis" aria-label="Indicadores">
          <div className="kpi">
            <span>Notas abiertas</span>
            <strong>4</strong>
            <Sparkline values={[1, 2, 2, 3, 4]} />
          </div>
          <div className="kpi is-lock">
            <span>Sala completa</span>
            <strong className="kpi-redact">••••</strong>
            <em>Censurado</em>
          </div>
          <div className="kpi is-lock accent">
            <span>Alertas</span>
            <strong className="kpi-redact">••••</strong>
            <em>Censurado</em>
          </div>
          <div className="kpi is-lock">
            <span>Fuentes</span>
            <strong className="kpi-redact">••••</strong>
            <em>Censurado</em>
          </div>
        </section>

        <div className="toolbar">
          <div className="disease-pills" role="group" aria-label="Enfermedades">
            <span className="pill-btn on">Todas</span>
            <span className="pill-btn is-lock">Gusano barrenador</span>
            <span className="pill-btn is-lock">Gripe aviar</span>
            <span className="pill-btn is-lock">PPC</span>
          </div>
          <button type="button" className="run" disabled>
            Ejecutar ciclo
          </button>
        </div>

        <div className="gate-map">
          <div className="gate-map-hit">
            <MapView points={geo} height={280} censor compact />
          </div>
          <div className="gate-map-veil">
            <p>Cobertura hasta ahora. Países, grafo y minería: censurados.</p>
            <p>Se prenden con la clave de arriba.</p>
          </div>
        </div>

        <section className="gate-freeze art-cards" aria-label="Notas">
          {articles.map((a) => (
            <ArticleCard key={a.content_id} article={a} />
          ))}
        </section>
      </div>
    </div>
  );
}
