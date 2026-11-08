import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { FilterIcon } from "../components/Icons";
import { api, severity, STATUS_LABELS } from "../api";

const SEVERITIES = ["Critical", "High", "Moderate", "Low"];
const STATUSES = ["not_contacted", "contacted", "needs_follow_up", "resolved"];

function toggle(list, value) {
  return list.includes(value) ? list.filter((v) => v !== value) : [...list, value];
}

export default function CallListPage() {
  const [queue, setQueue] = useState([]);
  const [error, setError] = useState(null);
  const [sevs, setSevs] = useState([]);
  const [statuses, setStatuses] = useState([]);
  const [search, setSearch] = useState("");
  const [filterOpen, setFilterOpen] = useState(false);
  const filterRef = useRef(null);
  const navigate = useNavigate();

  useEffect(() => {
    const load = () =>
      api.queue().then((data) => { setQueue(data); setError(null); }).catch((e) => setError(e.message));
    load();
    const timer = setInterval(load, 15000);
    return () => clearInterval(timer);
  }, []);

  // Close the filter panel on outside click or Escape
  useEffect(() => {
    if (!filterOpen) return;
    const onClick = (e) => { if (!filterRef.current?.contains(e.target)) setFilterOpen(false); };
    const onKey = (e) => { if (e.key === "Escape") setFilterOpen(false); };
    document.addEventListener("mousedown", onClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [filterOpen]);

  const activeCount = sevs.length + statuses.length;
  const clearAll = () => { setSevs([]); setStatuses([]); };

  const shown = queue.filter(
    (h) =>
      (sevs.length === 0 || sevs.includes(severity(h.score).label)) &&
      (statuses.length === 0 || statuses.includes(h.status)) &&
      h.address.toLowerCase().includes(search.toLowerCase()),
  );

  return (
    <>
      {error && <div className="error">Could not reach the API: {error}</div>}

      <div className="card">
        <div className="card-header">
          <span className="label">Call queue ›</span>
          <span className="muted">{shown.length} households</span>
        </div>
      <div className="filters">
        <div className="filter-row">
          <input className="search" placeholder="Search address..." value={search}
            onChange={(e) => setSearch(e.target.value)} />
          <div className="filter-wrap" ref={filterRef}>
            <button className={activeCount ? "btn filter-btn active" : "btn filter-btn"}
              onClick={() => setFilterOpen((o) => !o)} aria-expanded={filterOpen}>
              <FilterIcon /> Filter{activeCount > 0 && <span className="filter-count">{activeCount}</span>}
            </button>
            {filterOpen && (
              <div className="filter-panel">
                <div className="filter-group">
                  <div className="label">Severity</div>
                  {SEVERITIES.map((v) => (
                    <label key={v} className="check">
                      <input type="checkbox" checked={sevs.includes(v)} onChange={() => setSevs((l) => toggle(l, v))} />
                      {v}
                    </label>
                  ))}
                </div>
                <div className="filter-group">
                  <div className="label">Status</div>
                  {STATUSES.map((v) => (
                    <label key={v} className="check">
                      <input type="checkbox" checked={statuses.includes(v)} onChange={() => setStatuses((l) => toggle(l, v))} />
                      {STATUS_LABELS[v]}
                    </label>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
        {activeCount > 0 && (
          <div className="chips">
            {sevs.map((v) => (
              <button key={v} className="chip" onClick={() => setSevs((l) => toggle(l, v))} aria-label={`Remove ${v}`}>
                {v} <span aria-hidden>×</span>
              </button>
            ))}
            {statuses.map((v) => (
              <button key={v} className="chip" onClick={() => setStatuses((l) => toggle(l, v))} aria-label={`Remove ${STATUS_LABELS[v]}`}>
                {STATUS_LABELS[v]} <span aria-hidden>×</span>
              </button>
            ))}
            <button className="clear-link" onClick={clearAll}>Clear all</button>
          </div>
        )}
      </div>

      <div className="list">
        {shown.map((h) => {
          const s = severity(h.score);
          return (
            <div key={h.id} className="row" onClick={() => navigate(`/household/${h.id}`)}>
              <div className="rank">{String(h.rank).padStart(2, "0")}</div>
              <div className="row-main">
                <div className="row-title">{h.address}</div>
                <div className="row-reason">
                  {h.aiReason && <span className="ai-tag">AI</span>} {h.reason}
                </div>
                <div className="tags">
                  {h.summary.outageHours > 0 && <span className="tag neutral">Out {h.summary.outageHours}h</span>}
                  {h.summary.minTemp != null && <span className="tag neutral">Low {Math.round(h.summary.minTemp)}°F</span>}
                  {h.medicalDevice && <span className="tag risk">Medical device</span>}
                  {h.livesAlone && <span className="tag risk">Lives alone</span>}
                  {h.mobilityLimits && <span className="tag risk">Mobility limits</span>}
                  {h.callRequested && <span className="tag call">Asked for a call</span>}
                </div>
              </div>
              <div className="row-score">
                <span className={`badge ${s.cls}`}>{h.score} · {s.label}</span>
                <div className="bar"><div className={`bar-fill ${s.cls}`} style={{ width: `${Math.min(h.score, 100)}%` }} /></div>
              </div>
              <div className="row-status">{STATUS_LABELS[h.status]}</div>
            </div>
          );
        })}
        {shown.length === 0 && !error && <div className="empty">No households match these filters.</div>}
      </div>
      </div>
    </>
  );
}
