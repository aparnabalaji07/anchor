import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { pages, timeAgo } from "../api";

const TABS = { all: "All", pending_review: "Pending review", approved: "Approved", rejected: "Rejected" };
const STATUS_CLASS = { pending_review: "sev-high", approved: "ok", rejected: "sev-critical" };
const STATUS_TEXT = { pending_review: "Pending review", approved: "Approved", rejected: "Rejected" };

export default function ClaimsPage() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [tab, setTab] = useState("all");
  const navigate = useNavigate();

  useEffect(() => {
    const load = () =>
      pages.claimDrafts().then((d) => { setData(d); setError(null); }).catch((e) => setError(e.message));
    load();
    const timer = setInterval(load, 15000);
    return () => clearInterval(timer);
  }, []);

  if (!data) return error ? <div className="error">Could not reach the API: {error}</div> : <p>Loading...</p>;

  const count = (s) => data.drafts.filter((d) => d.status === s).length;
  const shown = data.drafts.filter((d) => tab === "all" || d.status === tab);

  return (
    <>
      {error && <div className="error">Could not reach the API: {error}</div>}
      <section className="card cf-card page-stats">
        <div className="cf-stats">
          <div className="cf-stat cf-critical"><div className="cf-num">{count("pending_review")}</div><div className="cf-label">Waiting for review</div></div>
          <div className="cf-stat"><div className="cf-num">{count("approved")}</div><div className="cf-label">Approved</div></div>
          <div className="cf-stat"><div className="cf-num">{count("rejected")}</div><div className="cf-label">Rejected</div></div>
          <div className="cf-stat"><div className="cf-num">{data.needsDraft.length}</div><div className="cf-label">Need a draft</div></div>
        </div>
      </section>

      <section className="card">
        <div className="card-header">
          <span className="label">Claim drafts ›</span>
          <div className="tabs-inline">
            {Object.entries(TABS).map(([k, text]) => (
              <button key={k} className={tab === k ? "pill active" : "pill"} onClick={() => setTab(k)}>{text}</button>
            ))}
          </div>
        </div>
        <div className="list">
          {shown.map((d) => (
            <div key={d.id} className="simple-row" onClick={() => navigate(`/household/${d.householdId}`)}>
              <div className="simple-main">
                <div className="row-title">
                  {d.address} {!d.simulated && <span className="tag live">● Live box</span>}
                </div>
                {d.summary && <div className="row-reason clamp">{d.summary}</div>}
                <div className="tags">
                  <span className="tag neutral">Drafted {timeAgo(d.createdAt)}</span>
                  {d.photoFields > 0 && <span className="tag photo">{d.photoFields} from photo</span>}
                  {d.confirmFields > 0 && <span className="tag confirm">{d.confirmFields} to confirm</span>}
                  {!d.aiUsed && <span className="tag neutral">No AI summary</span>}
                  {d.reviewedBy && <span className="tag neutral">Reviewed by {d.reviewedBy}</span>}
                </div>
              </div>
              <span className={`badge ${STATUS_CLASS[d.status]}`}>{STATUS_TEXT[d.status]}</span>
            </div>
          ))}
          {shown.length === 0 && <div className="empty">No claim drafts here yet.</div>}
        </div>
      </section>

      <section className="card stacked">
        <div className="card-header">
          <span className="label">Need a draft ›</span>
          <span className="muted">Asked for a call or sent photos, but no draft yet</span>
        </div>
        <div className="list">
          {data.needsDraft.map((h) => (
            <div key={h.householdId} className="simple-row" onClick={() => navigate(`/household/${h.householdId}`)}>
              <div className="simple-main">
                <div className="row-title">
                  {h.address} {!h.simulated && <span className="tag live">● Live box</span>}
                </div>
                <div className="tags">
                  {h.callRequested && <span className="tag call">Asked for a call</span>}
                  {h.photos > 0 && <span className="tag photo">{h.photos} {h.photos === 1 ? "photo" : "photos"}</span>}
                </div>
              </div>
              <span className="muted link">Open ›</span>
            </div>
          ))}
          {data.needsDraft.length === 0 && <div className="empty">Every household that asked for help has a draft.</div>}
        </div>
      </section>
    </>
  );
}
