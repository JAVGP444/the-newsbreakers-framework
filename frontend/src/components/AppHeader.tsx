import { useEffect, useState, type ReactNode } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { api } from "../api";
import { TranslateToggle } from "../translate";
import BrandMark from "./BrandMark";
import VerdictLegend from "./VerdictLegend";

const NAV = [
  { to: "/", label: "Sala", end: true },
  { to: "/revision", label: "Revisión" },
  { to: "/mapa", label: "Mapa" },
  { to: "/graficas", label: "Gráficas" },
  { to: "/grafo", label: "Grafo" },
  { to: "/cnn", label: "CNN" },
  { to: "/fuentes", label: "Fuentes" },
];

export default function AppHeader({
  title,
  subtitle,
  actions,
}: {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
}) {
  const location = useLocation();
  const search = location.search;
  const [pending, setPending] = useState(0);

  useEffect(() => {
    let cancelled = false;
    const load = () => {
      api
        .kpis()
        .then((r) => {
          if (!cancelled) setPending(Number(r.alerts_pending || 0));
        })
        .catch(() => {
          /* no borrar el recuento anterior */
        });
    };
    load();
    const t = window.setInterval(load, 60_000);
    return () => {
      cancelled = true;
      window.clearInterval(t);
    };
  }, [location.pathname]);

  return (
    <header className="site-header">
      <div className="site-header-inner">
        <div className="brand-block">
          <BrandMark />
          <div>
            <p className="kicker">The NewsBreakers</p>
            <h1>{title}</h1>
            {subtitle ? <p className="muted header-sub">{subtitle}</p> : null}
          </div>
        </div>
        <div className="top-actions">
          <TranslateToggle />
          {actions}
        </div>
      </div>
      <nav className="site-nav" aria-label="Secciones del observatorio">
        {NAV.map((item) => (
          <NavLink
            key={item.to}
            to={{ pathname: item.to, search }}
            end={item.end}
            className={({ isActive }) => {
              const salaOn = item.to === "/" && (location.pathname === "/" || location.pathname === "/sala");
              return isActive || salaOn ? "nav-link on" : "nav-link";
            }}
          >
            {item.label}
            {item.to === "/revision" && pending > 0 ? <span className="nav-badge">{pending}</span> : null}
          </NavLink>
        ))}
      </nav>
      {!location.pathname.startsWith("/article") ? <VerdictLegend /> : null}
    </header>
  );
}
