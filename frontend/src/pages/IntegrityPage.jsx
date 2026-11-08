import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { pages, timeAgo } from "../api";

function ChainBadge({ h }) {
  if (h.status === "verified") return <span className="badge ok">Verified</span>;
  if (h.status === "tampered") return <span className="badge sev-critical">Tampered at reading {h.firstBadCounter}</span>;
  return <span className="badge neutral">No data yet</span>;
}

export default function IntegrityPage() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    const load = () =>
      pages.integrity().then((d) => { setData(d); setError(null); }).catch((e) => setError(e.message));
    load();
    const timer = setInterval(load, 30000);
    return () => clearInterval(timer);
  }, []);

  if (!data) return error ? <div className="error">Could not reach the API: {error}</div> : <p>Checking evidence...</p>;

  const withData = data.households.filter((h) => h.status !== "no_data");
  const verified = withData.filter((h) => h.status === "verified").length;
  const tampered = withData.length - verified;
  const q = search.toLowerCase();
  const shown = data.households.filter((h) => h.address.toLowerCase().includes(q) || h.deviceId.toLowerCase().includes(q));

  return (
    <>
      {error && <div className="error">Could not reach the API: {error}</div>}
      <section className="card cf-card page-stats">
        <div className="cf-stats">
          <div className={tampered ? "cf-stat cf-critical" : "cf-stat cf-good"}>
            <div className="cf-num">{verified}/{withData.length}</div><div className="cf-label">Chains verified</div>
          </div>
          <div className={tampered ? "cf-stat cf-critical" : "cf-stat"}>
            <div className="cf-num">{tampered}</div><div className="cf-label">Tampered</div>
          </div>
          <div className={data.photos.changed ? "cf-stat cf-critical" : "cf-stat"}>
            <div className="cf-num">{data.photos.verified}/{data.photos.total}</div><div className="cf-label">Photos unchanged</div>
          </div>
          <div className="cf-stat">
            <div className="cf-num">{data.rejected24h}</div><div className="cf-label">Fakes blocked (24h)</div>
          </div>
        </div>
        <p className="muted integrity-note">
          Each reading stores a SHA-256 hash of itself and the reading before it, so changing or deleting
          any reading breaks the chain from that point on. Photos are checked against the hash saved at upload.
        </p>
      </section>

      <section className="card">
        <div className="card-header">
          <span className="label">Evidence chains ›</span>
          <span className="muted">{data.households.length} boxes</span>
        </div>
        <div className="filters">
          <div className="filter-row">
            <input className="search" placeholder="Search address or device..." value={search}
              onChange={(e) => setSearch(e.target.value)} />
          </div>
        </div>
        <div className="list">
          {shown.map((h) => (
            <div key={h.id} className="simple-row" onClick={() => navigate(`/household/${h.id}`)}>
              <div className="simple-main">
                <div className="row-title">
                  {h.address} {!h.simulated && <span className="tag live">● Live box</span>}
                </div>
                <div className="row-sub">
                  <span className="mono">{h.deviceId}</span> · {h.readingsChecked} readings checked
                  {h.lastReading && ` · last reading ${timeAgo(h.lastReading)}`}
                  {h.reason && ` · ${h.reason.replace(/_/g, " ")}`}
                </div>
              </div>
              <ChainBadge h={h} />
            </div>
          ))}
          {shown.length === 0 && <div className="empty">No boxes match.</div>}
        </div>
      </section>

      <section className="card stacked">
        <div className="card-header">
          <span className="label">Blocked messages ›</span>
          <span className="muted">Rejected because the signature, device or counter was wrong</span>
        </div>
        <div className="list">
          {data.rejected.map((r) => (
            <div key={r.id} className="simple-row static">
              <div className="simple-main">
                <div className="row-title">{r.reason.replace(/_/g, " ")}</div>
                <div className="row-sub"><span className="mono">{r.deviceId || "unknown device"}</span> · {new Date(r.receivedAt).toLocaleString()}</div>
              </div>
              <span className="badge sev-critical">Blocked</span>
            </div>
          ))}
          {data.rejected.length === 0 && <div className="empty">No fake messages so far.</div>}
        </div>
      </section>
    </>
  );
}
