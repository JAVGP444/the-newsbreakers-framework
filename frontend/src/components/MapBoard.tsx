import { useEffect, useMemo, useState } from "react";
import type { GeoRow } from "../api";
import { MAP_DISEASE_COLOR, mapDiseaseStyle, riskHint } from "../display";
import { pointKey } from "../geoCentroids";
import { useLocale } from "../locale";
import MapView from "./MapView";

function diseaseLabel(row: GeoRow, lang: "es" | "en") {
  return mapDiseaseStyle(row.disease || row.diseases?.[0], lang).label;
}

export default function MapBoard({
  points,
  unlocated,
  onOpenSala,
}: {
  points: GeoRow[];
  unlocated: GeoRow[];
  onOpenSala: (point: GeoRow) => void;
}) {
  const { t, lang } = useLocale();
  const [picked, setPicked] = useState<GeoRow | null>(null);
  const [q, setQ] = useState("");

  useEffect(() => {
    if (!picked) return;
    if (!points.some((p) => pointKey(p) === pointKey(picked))) setPicked(null);
  }, [points, picked]);

  const rows = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return points.filter((p) => {
      if (!needle) return true;
      const blob = `${p.name} ${p.country} ${p.disease || ""} ${(p.diseases || []).join(" ")}`.toLowerCase();
      return blob.includes(needle);
    });
  }, [points, q]);

  const locatedNotes = points.reduce((n, p) => n + (p.count || 0), 0);
  const lostNotes = unlocated.reduce((n, r) => n + (r.count || 0), 0);
  const hot = points.find((p) => (p.risk_mean || 0) >= 70);

  if (!points.length && !unlocated.length) {
    return (
      <section className="viz">
        <h3>{t("map.emptyTitle")}</h3>
        <p className="muted">{t("map.empty")}</p>
      </section>
    );
  }

  return (
    <section className="graph-board map-board">
      <p className="graph-howto">
        {t("map.howto")}
      </p>
      <p className="graph-legend">
        {Object.entries(MAP_DISEASE_COLOR).map(([id]) => (
          <span key={id}>
            <i className="swatch" style={{ background: MAP_DISEASE_COLOR[id].fill }} /> {mapDiseaseStyle(id, lang).label}
          </span>
        ))}
        <span>
          <i className="swatch" style={{ background: "#94a3b8" }} /> {t("disease.mixed")}
        </span>
        <span className="muted">
          {t("map.places", { n: points.length, notes: locatedNotes })}
          {lostNotes ? t("map.unlocated", { n: lostNotes }) : ""}
          {hot ? t("map.hot", { name: hot.name }) : ""}
        </span>
      </p>
      <div className="graph-split">
        <MapView points={points} height={560} selectedId={picked ? pointKey(picked) : null} onSelect={setPicked} />
        <aside className="graph-rels" aria-label="Lugares del mapa">
          <div className="graph-rels-head">
            <h4>{t("map.look")}</h4>
            <p className="muted">{picked ? picked.name : t("map.placesN", { n: rows.length })}</p>
            <input
              type="search"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder={t("map.search")}
              aria-label={t("map.searchAria")}
            />
            {picked ? (
              <button type="button" className="ghost" onClick={() => setPicked(null)}>
                {t("map.all")}
              </button>
            ) : null}
          </div>
          <div className="graph-rels-body">
            {rows.length ? (
              <table>
                <thead>
                  <tr>
                    <th>{t("map.col.place")}</th>
                    <th>{t("map.col.notes")}</th>
                    <th>{t("map.col.what")}</th>
                    <th>{t("map.col.since")}</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((p) => (
                    <tr
                      key={pointKey(p)}
                      className={picked && pointKey(picked) === pointKey(p) ? "on" : ""}
                      onClick={() => setPicked(p)}
                    >
                      <td>
                        <strong>{p.name}</strong>
                        <em>
                          {p.grain === "place" ? t("map.grain.place") : t("map.grain.country")}
                          {p.risk_mean != null ? ` · ${t("map.riskWord")} ${riskHint(p.risk_mean, lang)}` : ""}
                        </em>
                      </td>
                      <td className="rel">{p.count}</td>
                      <td>{diseaseLabel(p, lang)}</td>
                      <td className="rel">{p.first_seen || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="muted">{t("map.none")}</p>
            )}
          </div>
        </aside>
      </div>
      {picked ? (
        <div className="graph-pick map-pick">
          <div>
            <strong>{picked.name}</strong>
            <em>
              {" "}
              · {t("map.notesN", { n: picked.count })} · {diseaseLabel(picked, lang)}
              {picked.risk_mean != null ? ` · ${t("map.riskWord")} ${riskHint(picked.risk_mean, lang)}` : ""}
              {picked.first_seen ? ` · ${t("map.since", { date: picked.first_seen })}` : ""}
            </em>
            {picked.articles?.length ? (
              <ul className="map-pick-arts">
                {picked.articles.slice(0, 3).map((a) => (
                  <li key={a.content_id}>{a.title}</li>
                ))}
              </ul>
            ) : null}
          </div>
          <button type="button" className="run" onClick={() => onOpenSala(picked)}>
            {t("map.openSala")}
          </button>
        </div>
      ) : (
        <p className="muted">{t("map.pickHint")}</p>
      )}
      {lostNotes ? (
        <p className="muted unlocated-line">
          {t("map.unlocatedLine", { n: lostNotes, list: unlocated.map((u) => `${u.name} ${u.count}`).join(" · ") })}
        </p>
      ) : null}
    </section>
  );
}
