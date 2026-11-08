import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { api, severity, STATUS_LABELS } from "../api";

const SEVERITIES = ["Critical", "High", "Moderate", "Low"];
const COLORS = { Critical: "#c8372d", High: "#c26a12", Moderate: "#b8920c", Low: "#a5a5a0" };

export default function MapPage() {
  const [queue, setQueue] = useState([]);
  const [error, setError] = useState(null);
  const [hidden, setHidden] = useState([]);
  const [hideResolved, setHideResolved] = useState(false);
  const mapEl = useRef(null);
  const mapRef = useRef(null);
  const layerRef = useRef(null);
  const fitted = useRef(false);
  const navigate = useNavigate();

  useEffect(() => {
    const load = () =>
      api.queue().then((q) => { setQueue(q || []); setError(null); }).catch((e) => setError(e.message));
    load();
    const timer = setInterval(load, 15000);
    return () => clearInterval(timer);
  }, []);

  // Create the map once
  useEffect(() => {
    const map = L.map(mapEl.current, { zoomControl: true, scrollWheelZoom: true }).setView([33.1, -96.8], 11);
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 19,
    }).addTo(map);
    layerRef.current = L.layerGroup().addTo(map);
    mapRef.current = map;
    return () => { map.remove(); mapRef.current = null; };
  }, []);

  const located = useMemo(() => queue.filter((h) => h.lat != null && h.lng != null), [queue]);
  const shown = useMemo(
    () => located.filter(
      (h) => !hidden.includes(severity(h.score).label) && !(hideResolved && h.status === "resolved"),
    ),
    [located, hidden, hideResolved],
  );

  // Redraw markers when the data or filters change
  useEffect(() => {
    const layer = layerRef.current;
    if (!layer) return;
    layer.clearLayers();
    // Draw low scores first so critical homes sit on top
    for (const h of [...shown].sort((a, b) => a.score - b.score)) {
      const s = severity(h.score);
      const resolved = h.status === "resolved";
      const marker = L.circleMarker([h.lat, h.lng], {
        radius: h.simulated ? 6 + Math.min(h.score, 100) / 25 : 11,
        color: h.simulated ? "#ffffff" : "#1a1a19",
        weight: h.simulated ? 1.5 : 3,
        fillColor: resolved ? "#c9c9c4" : COLORS[s.label],
        fillOpacity: resolved ? 0.6 : 0.9,
      });

      const box = document.createElement("div");
      box.className = "map-pop";
      const title = document.createElement("div");
      title.className = "map-pop-title";
      title.textContent = h.address;
      const meta = document.createElement("div");
      meta.className = "map-pop-meta";
      meta.textContent = `${h.score} · ${s.label} · ${STATUS_LABELS[h.status]}${h.summary.outageHours ? ` · out ${h.summary.outageHours}h` : ""}${h.simulated ? "" : " · Live box"}`;
      const btn = document.createElement("button");
      btn.className = "btn small";
      btn.textContent = "Open household";
      btn.onclick = () => navigate(`/household/${h.id}`);
      box.append(title, meta, btn);

      marker.bindPopup(box).bindTooltip(h.address.split(",")[0], { direction: "top", offset: [0, -6] });
      layer.addLayer(marker);
    }
  }, [shown, navigate]);

  // Zoom to fit all homes the first time data arrives
  useEffect(() => {
    if (fitted.current || !mapRef.current || located.length === 0) return;
    mapRef.current.fitBounds(L.latLngBounds(located.map((h) => [h.lat, h.lng])), { padding: [30, 30] });
    fitted.current = true;
  }, [located]);

  const toggle = (label) => setHidden((l) => (l.includes(label) ? l.filter((v) => v !== label) : [...l, label]));
  const outNow = queue.filter((h) => h.outNow).length;

  return (
    <>
      {error && <div className="error">Could not reach the API: {error}</div>}
      <section className="card">
        <div className="card-header">
          <span className="label">Outage map ›</span>
          <span className="muted">
            {shown.length} of {located.length} households{outNow > 0 && ` · ${outNow} out right now`}
          </span>
        </div>
        <div className="map-legend">
          {SEVERITIES.map((label) => (
            <button key={label} className={hidden.includes(label) ? "legend-toggle off" : "legend-toggle"}
              onClick={() => toggle(label)} aria-pressed={!hidden.includes(label)}>
              <span className="legend-dot" style={{ background: COLORS[label] }} /> {label}
            </button>
          ))}
          <button className={hideResolved ? "legend-toggle off" : "legend-toggle"}
            onClick={() => setHideResolved((v) => !v)} aria-pressed={!hideResolved}>
            <span className="legend-dot" style={{ background: "#c9c9c4" }} /> Resolved
          </button>
          <span className="legend-note"><span className="legend-dot live" /> Live box</span>
          <span className="legend-note muted">Bigger dot = higher score</span>
        </div>
        <div ref={mapEl} className="map" />
      </section>
    </>
  );
}
