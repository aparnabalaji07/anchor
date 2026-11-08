import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, severity, STATUS_LABELS } from "../api";

const SEVERITIES = ["All", "Critical", "High", "Moderate", "Low"];
const STATUSES = ["all", "not_contacted", "contacted", "needs_follow_up", "resolved"];

export default function CallListPage() {
  const [queue, setQueue] = useState([]);
  const [error, setError] = useState(null);
  const [sev, setSev] = useState("All");
  const [status, setStatus] = useState("all");
  const [search, setSearch] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    const load = () =>
      api.queue().then((data) => { setQueue(data); setError(null); }).catch((e) => setError(e.message));
    load();
    const timer = setInterval(load, 15000);
    return () => clearInterval(timer);
  }, []);

  const shown = queue.filter(
    (h) =>
      (sev === "All" || severity(h.score).label === sev) &&
      (status === "all" || h.status === status) &&
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
        <input className="search" placeholder="Search address..." value={search}
          onChange={(e) => setSearch(e.target.value)} />
        <div className="pills">
          {SEVERITIES.map((s) => (
            <button key={s} className={sev === s ? "pill active" : "pill"} onClick={() => setSev(s)}>{s}</button>
          ))}
        </div>
        <div className="pills">
          {STATUSES.map((s) => (
            <button key={s} className={status === s ? "pill active" : "pill"} onClick={() => setStatus(s)}>
              {s === "all" ? "All" : STATUS_LABELS[s]}
            </button>
          ))}
        </div>
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
