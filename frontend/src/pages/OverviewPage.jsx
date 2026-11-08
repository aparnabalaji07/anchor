import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import AreaChart from "../components/AreaChart";
import { ClockIcon } from "../components/Icons";
import { api, extra, severity, STATUS_LABELS } from "../api";

const RANGES = { "6H": 6, "12H": 12, "24H": 24, ALL: 1000 };

export default function OverviewPage() {
  const [queue, setQueue] = useState([]);
  const [stats, setStats] = useState(null);
  const [range, setRange] = useState("24H");
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    const load = () =>
      Promise.all([api.queue(), extra.stats()])
        .then(([q, s]) => { setQueue(q); setStats(s); setError(null); })
        .catch((e) => setError(e.message));
    load();
    const timer = setInterval(load, 15000);
    return () => clearInterval(timer);
  }, []);

  const affected = queue.filter((h) => h.summary.outageHours > 0);
  const reached = affected.filter((h) => h.status !== "not_contacted");
  const notReached = affected.length - reached.length;
  const critical = queue.filter((h) => h.score >= 70 && h.status !== "resolved");
  const pct = affected.length ? Math.round((reached.length / affected.length) * 100) : 0;
  const hardest = stats?.zipsByOutage?.[0];
  const topAi = queue.find((h) => h.aiReason && h.status !== "resolved");

  const timeline = stats ? stats.timeline.slice(-RANGES[range]) : [];
  const points = timeline.map((t) => ({ value: t.withoutPower }));
  const peak = Math.max(0, ...timeline.map((t) => t.withoutPower));
  const now = timeline.length ? timeline[timeline.length - 1].withoutPower : 0;

  return (
    <>
      {error && <div className="error">Could not reach the API: {error}</div>}
      <div className="dash">
        <div className="dash-main">
          <section className="card">
            <div className="card-header">
              <span className="label">Call first ›</span>
              <Link to="/queue" className="muted link">View all</Link>
            </div>
            <div className="card-body split">
              <div>
                <div className="big-number">{critical.length}</div>
                <div className="delta">critical households still open</div>
                <div className="mini-stats">
                  <div><span className="label">Asked for a call</span><strong>{queue.filter((h) => h.callRequested).length}</strong></div>
                  <div><span className="label">Medical device</span><strong>{queue.filter((h) => h.medicalDevice).length}</strong></div>
                  <div><span className="label">Lives alone</span><strong>{queue.filter((h) => h.livesAlone).length}</strong></div>
                </div>
              </div>
              <div>
                <div className="label list-title">Top of the queue</div>
                {queue.slice(0, 5).map((h) => {
                  const s = severity(h.score);
                  return (
                    <div key={h.id} className="tx" onClick={() => navigate(`/household/${h.id}`)}>
                      <span className={`tx-dot ${s.cls}`} />
                      <div className="tx-main">
                        <div className="tx-title">{h.address.split(",")[0]}</div>
                        <div className="tx-sub">Out {h.summary.outageHours}h · {STATUS_LABELS[h.status]}</div>
                      </div>
                      <div className="tx-amount">{h.score}</div>
                    </div>
                  );
                })}
              </div>
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
            <div className="card-header"><span className="label">AI brief</span></div>
            <div className="card-body">
              <div className="serif-title">Your outage recap</div>
              <div className="muted clamp">{topAi ? topAi.reason : "Generate AI reasons to see a summary here."}</div>
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
