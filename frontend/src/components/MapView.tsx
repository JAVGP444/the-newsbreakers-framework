import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import iconRetinaUrl from "leaflet/dist/images/marker-icon-2x.png";
import iconUrl from "leaflet/dist/images/marker-icon.png";
import shadowUrl from "leaflet/dist/images/marker-shadow.png";
import type { GeoRow } from "../api";
import { mapDiseaseStyle, riskHint } from "../display";
import { plottablePoints, pointKey } from "../geoCentroids";
import { articleHref } from "../safeUrl";
import { useLocale } from "../locale";

delete (L.Icon.Default.prototype as unknown as { _getIconUrl?: unknown })._getIconUrl;
L.Icon.Default.mergeOptions({ iconRetinaUrl, iconUrl, shadowUrl });

type MarkerMeta = { circle: L.CircleMarker; stroke: string; weight: number };

type Props = {
  points: GeoRow[];
  height?: number;
  onSelect?: (point: GeoRow) => void;
  selectedId?: string | null;
  focus?: { lat: number; lng: number; label?: string } | null;
  censor?: boolean;
  compact?: boolean;
};

function escapeHtml(s: string) {
  return s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c] || c));
}

function radiusPx(count: number, max: number, compact: boolean) {
  const cap = compact ? 8 : 16;
  if (max <= 1) return compact ? 6 : 9;
  return (compact ? 5 : 7) + Math.sqrt(count / max) * cap;
}

function diseaseOf(p: GeoRow) {
  return p.disease || p.diseases?.[0] || "";
}

export default function MapView({
  points,
  height = 480,
  onSelect,
  selectedId = null,
  focus,
  censor = false,
  compact = false,
}: Props) {
  const { t, lang } = useLocale();
  const hostRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const markersRef = useRef<Map<string, MarkerMeta>>(new Map());
  const onSelectRef = useRef(onSelect);
  const selectedRef = useRef(selectedId);
  onSelectRef.current = onSelect;
  selectedRef.current = selectedId;

  useEffect(() => {
    const host = hostRef.current;
    if (!host) return;
    let cancelled = false;
    const rows = plottablePoints(points);

    function paint(map: L.Map) {
      markersRef.current.forEach((m) => m.circle.remove());
      markersRef.current.clear();
      const max = Math.max(...rows.map((p) => p.count || 1), 1);
      const bounds: L.LatLngExpression[] = [];
      for (const p of rows) {
        if (p.lat == null || p.lng == null) continue;
        const style = mapDiseaseStyle(diseaseOf(p), lang);
        const hot = (p.risk_mean || 0) >= 70;
        const weight = hot ? 2.5 : 1.5;
        const stroke = hot ? "#f59e0b" : style.stroke;
        const circle = L.circleMarker([p.lat, p.lng], {
          radius: radiusPx(p.count || 1, max, compact),
          color: stroke,
          weight,
          fillColor: style.fill,
          fillOpacity: 0.78,
          className: "obs-marker",
        }).addTo(map);
        const key = pointKey(p);
        markersRef.current.set(key, { circle, stroke, weight });
        if (censor) {
          circle.bindPopup(
            `<div class="obs-pop"><strong>${escapeHtml(t("map.censorTitle"))}</strong><span>${escapeHtml(t("map.censorBody"))}</span></div>`
          );
        } else {
          const disease = mapDiseaseStyle(diseaseOf(p), lang).label;
          const risk = p.risk_mean != null ? ` · ${t("map.riskWord")} ${riskHint(p.risk_mean, lang)}` : "";
          const grain = p.grain === "place" ? t("map.grain.named") : t("map.grain.countryShort");
          const arts = (p.articles || [])
            .slice(0, 3)
            .map(
              (a) =>
                `<a class="obs-pop-link" href="#${articleHref(a.content_id)}">${escapeHtml(a.title || a.content_id)}</a>`
            )
            .join("");
          circle.bindPopup(
            `<div class="obs-pop"><strong>${escapeHtml(p.name)}</strong><span>${escapeHtml(
              t("map.pop.line", { n: p.count, disease, risk, grain })
            )}</span>${arts}</div>`
          );
          circle.on("click", () => onSelectRef.current?.(p));
        }
        bounds.push([p.lat, p.lng]);
      }
      if (focus) {
        L.marker([focus.lat, focus.lng]).addTo(map).bindPopup(focus.label || t("article.place"));
        map.setView([focus.lat, focus.lng], compact ? 4 : 6);
      } else if (bounds.length === 1) {
        map.setView(bounds[0], compact ? 3 : 5);
      } else if (bounds.length) {
        map.fitBounds(bounds as L.LatLngBoundsExpression, {
          padding: compact ? [20, 20] : [36, 36],
          maxZoom: compact ? 3 : 6,
          animate: false,
        });
      } else if (!compact) {
        map.setView([24, -97], 4);
      }
      map.invalidateSize({ animate: false });
      applySelection(selectedRef.current);
    }

    function applySelection(id: string | null | undefined) {
      markersRef.current.forEach((meta, key) => {
        const on = Boolean(id && key === id);
        meta.circle.setStyle({
          weight: on ? 3.5 : meta.weight,
          color: on ? "#f8fafc" : meta.stroke,
        });
        if (on) meta.circle.openPopup();
      });
    }

    function draw() {
      if (cancelled || !host || host.clientWidth < 80) return;
      mapRef.current?.remove();
      mapRef.current = null;
      const map = L.map(host, {
        zoomControl: !compact,
        attributionControl: !compact,
        dragging: !compact,
        scrollWheelZoom: !compact,
        doubleClickZoom: !compact,
        boxZoom: false,
        keyboard: false,
        worldCopyJump: false,
      });
      L.tileLayer(
        "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}",
        {
          attribution: compact ? "" : "Tiles &copy; Esri",
          maxZoom: compact ? 8 : 12,
          noWrap: true,
        }
      ).addTo(map);
      map.setView(compact ? [14, -78] : [24, -97], compact ? 2 : 4);
      paint(map);
      mapRef.current = map;
    }

    const start = window.setTimeout(draw, 40);
    const ro = new ResizeObserver(() => {
      if (mapRef.current) mapRef.current.invalidateSize({ animate: false });
      else draw();
    });
    ro.observe(host);
    return () => {
      cancelled = true;
      window.clearTimeout(start);
      ro.disconnect();
      markersRef.current.clear();
      mapRef.current?.remove();
      mapRef.current = null;
    };
  }, [points, focus, censor, compact, lang, t]);

  useEffect(() => {
    const id = selectedId;
    markersRef.current.forEach((meta, key) => {
      const on = Boolean(id && key === id);
      meta.circle.setStyle({
        weight: on ? 3.5 : meta.weight,
        color: on ? "#f8fafc" : meta.stroke,
      });
      if (on) meta.circle.openPopup();
    });
  }, [selectedId]);

  return (
    <div className={compact ? "leaflet-frame is-compact" : "leaflet-frame"} style={{ height }}>
      <div ref={hostRef} className="leaflet-host" />
    </div>
  );
}
