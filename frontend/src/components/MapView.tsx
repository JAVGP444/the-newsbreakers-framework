import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import iconRetinaUrl from "leaflet/dist/images/marker-icon-2x.png";
import iconUrl from "leaflet/dist/images/marker-icon.png";
import shadowUrl from "leaflet/dist/images/marker-shadow.png";
import type { GeoRow } from "../api";
import { articleHref } from "../safeUrl";
import { plottablePoints } from "../geoCentroids";

delete (L.Icon.Default.prototype as unknown as { _getIconUrl?: unknown })._getIconUrl;
L.Icon.Default.mergeOptions({ iconRetinaUrl, iconUrl, shadowUrl });

type Props = {
  points: GeoRow[];
  height?: number;
  onSelect?: (point: GeoRow) => void;
  focus?: { lat: number; lng: number; label?: string } | null;
  censor?: boolean;
  compact?: boolean;
};

function escapeHtml(s: string) {
  return s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c] || c));
}

function radiusPx(count: number, max: number, compact: boolean) {
  const cap = compact ? 7 : 8;
  if (max <= 1) return compact ? 6 : 7;
  return (compact ? 5 : 5) + Math.sqrt(count / max) * cap;
}

export default function MapView({
  points,
  height = 480,
  onSelect,
  focus,
  censor = false,
  compact = false,
}: Props) {
  const hostRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const onSelectRef = useRef(onSelect);
  onSelectRef.current = onSelect;

  useEffect(() => {
    const host = hostRef.current;
    if (!host) return;
    let cancelled = false;
    const rows = plottablePoints(points);

    function paint(map: L.Map) {
      const max = Math.max(...rows.map((p) => p.count || 1), 1);
      const bounds: L.LatLngExpression[] = [];
      for (const p of rows) {
        if (p.lat == null || p.lng == null) continue;
        const circle = L.circleMarker([p.lat, p.lng], {
          radius: radiusPx(p.count || 1, max, compact),
          color: "#5eead4",
          weight: 1.5,
          fillColor: "#2dd4bf",
          fillOpacity: 0.7,
          className: "obs-marker",
        }).addTo(map);
        if (censor) {
          circle.bindPopup(
            `<div class="obs-pop"><strong>Censurado</strong><span>Hay cobertura aquí. El país se abre con la clave.</span></div>`
          );
        } else {
          const arts = (p.articles || [])
            .slice(0, 4)
            .map(
              (a) =>
                `<a class="obs-pop-link" href="#${articleHref(a.content_id)}">${escapeHtml(a.title || a.content_id)}</a>`
            )
            .join("");
          circle.bindPopup(
            `<div class="obs-pop"><strong>${escapeHtml(p.name)}</strong><span>${p.count} documentos. Pulsa para verlos en la sala.</span>${arts}</div>`
          );
          circle.on("click", () => onSelectRef.current?.(p));
        }
        bounds.push([p.lat, p.lng]);
      }
      if (focus) {
        L.marker([focus.lat, focus.lng]).addTo(map).bindPopup(focus.label || "Ubicación");
        map.setView([focus.lat, focus.lng], 4);
      } else if (bounds.length === 1) {
        map.setView(bounds[0], compact ? 3 : 4);
      } else if (bounds.length) {
        map.fitBounds(bounds as L.LatLngBoundsExpression, {
          padding: compact ? [20, 20] : [28, 28],
          maxZoom: compact ? 3 : 4,
          animate: false,
        });
      }
      map.invalidateSize({ animate: false });
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
          maxZoom: 8,
          noWrap: true,
        }
      ).addTo(map);
      map.setView([14, -78], compact ? 2 : 2);
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
      mapRef.current?.remove();
      mapRef.current = null;
    };
  }, [points, focus, censor, compact]);

  return (
    <div className={compact ? "leaflet-frame is-compact" : "leaflet-frame"} style={{ height }}>
      <div ref={hostRef} className="leaflet-host" />
    </div>
  );
}
