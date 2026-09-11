import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import iconRetinaUrl from "leaflet/dist/images/marker-icon-2x.png";
import iconUrl from "leaflet/dist/images/marker-icon.png";
import shadowUrl from "leaflet/dist/images/marker-shadow.png";
import type { GeoRow } from "../api";
import { articleHref } from "../safeUrl";

delete (L.Icon.Default.prototype as unknown as { _getIconUrl?: unknown })._getIconUrl;
L.Icon.Default.mergeOptions({ iconRetinaUrl, iconUrl, shadowUrl });

type Props = {
  points: GeoRow[];
  height?: number;
  onSelect?: (point: GeoRow) => void;
  focus?: { lat: number; lng: number; label?: string } | null;
};

function escapeHtml(s: string) {
  return s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c] || c));
}

export default function MapView({ points, height = 480, onSelect, focus }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const onSelectRef = useRef(onSelect);
  onSelectRef.current = onSelect;

  useEffect(() => {
    if (!ref.current) return;
    if (mapRef.current) {
      mapRef.current.remove();
      mapRef.current = null;
    }
    const map = L.map(ref.current, { zoomControl: true, attributionControl: true }).setView([20, -75], 3);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "&copy; OpenStreetMap",
      maxZoom: 12,
    }).addTo(map);

    const max = Math.max(...points.map((p) => p.count || 1), 1);
    const bounds: L.LatLngExpression[] = [];
    for (const p of points) {
      if (p.lat == null || p.lng == null) continue;
      const r = 10 + Math.sqrt((p.count || 1) / max) * 26;
      const circle = L.circleMarker([p.lat, p.lng], {
        radius: r,
        color: "#0b6e7a",
        weight: 2,
        fillColor: "#14b8a6",
        fillOpacity: 0.45 + ((p.count || 1) / max) * 0.35,
        className: "obs-marker",
      }).addTo(map);
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
      circle.on("mouseover", () => circle.setStyle({ weight: 3, fillOpacity: 0.85 }));
      circle.on("mouseout", () => circle.setStyle({ weight: 2, fillOpacity: 0.45 + ((p.count || 1) / max) * 0.35 }));
      bounds.push([p.lat, p.lng]);
    }
    if (focus) {
      L.marker([focus.lat, focus.lng]).addTo(map).bindPopup(focus.label || "Ubicación");
      map.setView([focus.lat, focus.lng], 4);
    } else if (bounds.length) {
      map.fitBounds(bounds as L.LatLngBoundsExpression, { padding: [36, 36], maxZoom: 5 });
    }
    mapRef.current = map;
    const t = window.setTimeout(() => map.invalidateSize(), 60);
    const t2 = window.setTimeout(() => map.invalidateSize(), 400);
    return () => {
      window.clearTimeout(t);
      window.clearTimeout(t2);
      map.remove();
      mapRef.current = null;
    };
  }, [points, focus]);

  return <div ref={ref} className="leaflet-host" style={{ height, minHeight: height }} />;
}
