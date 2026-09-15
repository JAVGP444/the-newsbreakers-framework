import { useEffect, useState, type ReactNode } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { api } from "../api";
import { LanguageToggle, useLocale } from "../locale";
import BrandMark from "./BrandMark";
import VerdictLegend from "./VerdictLegend";

const NAV = [
  { to: "/", key: "nav.sala", end: true },
  { to: "/revision", key: "nav.revision" },
  { to: "/mapa", key: "nav.mapa" },
  { to: "/graficas", key: "nav.graficas" },
  { to: "/grafo", key: "nav.grafo" },
  { to: "/cnn", key: "nav.cnn" },
  { to: "/fuentes", key: "nav.fuentes" },
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
  const { t } = useLocale();
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
          /* keep last count */
        });
    };
    load();
    const timer = window.setInterval(load, 60_000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
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
          <LanguageToggle />
          {actions}
        </div>
      </div>
      <nav className="site-nav" aria-label={t("nav.aria")}>
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
            {t(item.key)}
            {item.to === "/revision" && pending > 0 ? <span className="nav-badge">{pending}</span> : null}
          </NavLink>
        ))}
      </nav>
      {!location.pathname.startsWith("/article") ? <VerdictLegend /> : null}
    </header>
  );
}
