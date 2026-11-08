import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import AreaChart from "../components/AreaChart";
import { ClockIcon, SparkIcon } from "../components/Icons";
import { api, extra, severity, STATUS_LABELS } from "../api";

const RANGES = { "6H": 6, "12H": 12, "24H": 24, ALL: 1000 };

function timeAgo(iso, now) {
  const mins = Math.max(0, Math.floor((now - new Date(iso)) / 60000));
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins} min ago`;
  if (mins < 1440) return `${Math.floor(mins / 60)} h ago`;
  return `${Math.floor(mins / 1440)} d ago`;
}

export default function OverviewPage() {
  const [queue, setQueue] = useState([]);
  const [stats, setStats] = useState(null);
  const [brief, setBrief] = useState(null);
  const [clock, setClock] = useState(() => Date.now());
  const [refreshing, setRefreshing] = useState(false);
  const [refreshError, setRefreshError] = useState(null);
  const [range, setRange] = useState("24H");
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    const load = () =>
      // A missing brief should not stop the rest of the page from loading
      Promise.all([api.queue(), extra.stats(), extra.brief().catch(() => null)])
        .then(([q, s, b]) => { setQueue(q); setStats(s); setBrief(b); setClock(Date.now()); setError(null); })
        .catch((e) => setError(e.message));
    load();
    const timer = setInterval(load, 15000);
    return () => clearInterval(timer);
  }, []);

  // Rewrite ranking reasons for the top 15, then a new event brief from fresh facts
  async function refreshAi() {
    setRefreshing(true);
    setRefreshError(null);
    try {
      await extra.generateReasons(15).catch(() => setRefreshError("Some AI reasons could not be updated."));
      const b = await extra.createBrief();
      const q = await api.queue();
      setBrief(b);
      setQueue(q);
      setClock(Date.now());
    } catch {
      setRefreshError("Could not refresh the brief. Try again.");
    } finally {
      setRefreshing(false);
    }
  }

  const affected = queue.filter((h) => h.summary.outageHours > 0);
  const reached = affected.filter((h) => h.status !== "not_contacted");
  const notReached = affected.length - reached.length;
  const critical = queue.filter((h) => h.score >= 70 && h.status !== "resolved");
  const pct = affected.length ? Math.round((reached.length / affected.length) * 100) : 0;
  const hardest = stats?.zipsByOutage?.[0];
  const liveCount = queue.filter((h) => !h.simulated).length;
  const simCount = queue.length - liveCount;

  const timeline = stats ? stats.timeline.slice(-RANGES[range]) : [];
  const points = timeline.map((t) => ({ value: t.withoutPower }));
  const peak = Math.max(0, ...timeline.map((t) => t.withoutPower));
  const now = timeline.length ? timeline[timeline.length - 1].withoutPower : 0;

  return (
    <>
      {error && <div className="error">Could not reach the API: {error}</div>}
      <div className="dash">
        <div className="dash-main">
          <section className="card cf-card">
            <div className="card-header">
              <span className="label">Call first ›</span>
              <Link to="/queue" className="muted link">View all</Link>
            </div>
            <div className="cf-stats">
              <div className="cf-stat cf-critical">
                <div className="cf-num">{critical.length}</div>
                <div className="cf-label">Critical open</div>
              </div>
              <div className="cf-stat">
                <div className="cf-num">{queue.filter((h) => h.callRequested).length}</div>
                <div className="cf-label">Want a call</div>
              </div>
              <div className="cf-stat">
                <div className="cf-num">{queue.filter((h) => h.medicalDevice).length}</div>
                <div className="cf-label">Medical device</div>
              </div>
              <div className="cf-stat">
                <div className="cf-num">{queue.filter((h) => h.livesAlone).length}</div>
                <div className="cf-label">Live alone</div>
              </div>
            </div>
            <div className="cf-list">
              <div className="label cf-list-title">Top of the queue</div>
              {queue.slice(0, 5).map((h) => {
                const s = severity(h.score);
                return (
                  <div key={h.id} className="cf-row" onClick={() => navigate(`/household/${h.id}`)}>
                    <span className="cf-rank">{String(h.rank).padStart(2, "0")}</span>
                    <div className="cf-main">
                      <div className="tx-title">{h.address.split(",")[0]}</div>
                      <div className="tx-sub">Out {h.summary.outageHours}h · {STATUS_LABELS[h.status]}</div>
                    </div>
                    <span className={`badge ${s.cls}`}>{h.score} · {s.label}</span>
                  </div>
                );
              })}
            </div>
          </section>

          <section className="card">
            <div className="card-header">
              <span className="label">Households without power ›</span>
            </div>
            <div className="card-body">
              <div className="big-number">{peak}</div>
              <div className="delta">homes at the peak · {now} still without power · {affected.length} affected today</div>
              <AreaChart points={points} />
              {queue.length > 0 && (
                <div className="source-line">
                  {liveCount} live {liveCount === 1 ? "box" : "boxes"} · {simCount} simulated {simCount === 1 ? "household" : "households"}
                </div>
              )}
              <div className="range">
                {Object.keys(RANGES).map((r) => (
                  <button key={r} className={range === r ? "pill active" : "pill"} onClick={() => setRange(r)}>{r}</button>
                ))}
              </div>
              <Link to="/queue" className="btn wide">Open call queue</Link>
            </div>
          </section>
        </div>

        <aside className="dash-side">
          <section className="hero">
            <div className="label light">Outage event</div>
            {hardest ? (
              <>
                <div className="hero-title"><em>{hardest.zip}</em> was hit hardest</div>
                <div className="hero-sub">{hardest.households} {hardest.households === 1 ? "home" : "homes"} lost power</div>
              </>
            ) : (
              <div className="hero-title">No outages recorded yet</div>
            )}
            <div className="hero-pill"><ClockIcon /> {notReached} households not yet reached</div>
          </section>

          <section className="card">
            <div className="card-header">
              <span className="label">AI brief</span>
              <button className={refreshing ? "refresh-btn working" : "refresh-btn"} onClick={refreshAi} disabled={refreshing}>
                <SparkIcon /> {refreshing ? "Refreshing..." : "Refresh"}
              </button>
            </div>
            <div className="card-body">
              <div className="serif-title">Your outage recap</div>
              {brief ? (
                <>
                  <p className="brief-text">{brief.brief}</p>
                  <div className="brief-updated">Updated {timeAgo(brief.createdAt, clock)}</div>
                </>
              ) : (
                <div className="muted">No brief yet. Click Refresh to write one.</div>
              )}
              {refreshError && <div className="brief-error">{refreshError}</div>}
            </div>
          </section>

          <section className="card">
            <div className="card-header"><span className="label">Outreach progress ›</span></div>
            <div className="card-body">
              <div className="mid-number">{reached.length} <span className="muted">of {affected.length} reached</span></div>
              <div className="progress"><div style={{ width: `${pct}%` }} /></div>
              <div className="progress-pct">{pct}%</div>
            </div>
          </section>

          <section className="card">
            <div className="card-header"><span className="label">Security ›</span></div>
            <div className="card-body">
              <div className="mid-number">{stats ? stats.rejected24h : 0} <span className="muted">fake messages blocked</span></div>
              <div className="muted">
                {stats && Object.keys(stats.rejectedByReason).length
                  ? Object.entries(stats.rejectedByReason).map(([r, c]) => `${c} ${r.replace(/_/g, " ")}`).join(" · ")
                  : "No rejected messages in the last 24 hours"}
              </div>
            </div>
          </section>
        </aside>
      </div>
    </>
  );
}
