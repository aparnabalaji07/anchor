import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { BellIcon, HelpIcon } from "./Icons";
import { pages, timeAgo } from "../api";

const SEEN_KEY = "anchorNotificationsSeen";

function readSeen() {
  try { return Number(localStorage.getItem(SEEN_KEY)) || 0; } catch { return 0; }
}
function writeSeen(ms) {
  try { localStorage.setItem(SEEN_KEY, String(ms)); } catch { /* storage blocked, unread count just resets */ }
}

// Closes a dropdown on outside click or Escape
function useDismiss(open, setOpen, ref) {
  useEffect(() => {
    if (!open) return;
    const onClick = (e) => { if (!ref.current?.contains(e.target)) setOpen(false); };
    const onKey = (e) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("mousedown", onClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [open, setOpen, ref]);
}

export function NotificationsMenu() {
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState([]);
  const [seen, setSeen] = useState(readSeen);
  const ref = useRef(null);
  const navigate = useNavigate();
  useDismiss(open, setOpen, ref);

  useEffect(() => {
    const load = () => pages.notifications().then((n) => setItems(n || [])).catch(() => {});
    load();
    const timer = setInterval(load, 20000);
    return () => clearInterval(timer);
  }, []);

  const unread = items.filter((i) => new Date(i.time).getTime() > seen).length;

  function markRead() {
    const now = Date.now();
    writeSeen(now);
    setSeen(now);
  }

  function openItem(item) {
    setOpen(false);
    if (item.householdId) navigate(`/household/${item.householdId}`);
    else if (item.kind === "security") navigate("/integrity");
    else navigate("/queue");
  }

  return (
    <div className="account" ref={ref}>
      <button className="icon-btn" onClick={() => setOpen((o) => !o)} aria-expanded={open}
        aria-label={unread ? `Notifications, ${unread} new` : "Notifications"}>
        <BellIcon />
        {unread > 0 && <span className="notif-count">{unread > 9 ? "9+" : unread}</span>}
      </button>
      {open && (
        <div className="account-menu notif-menu">
          <div className="notif-head">
            <span className="account-name">Notifications</span>
            {unread > 0 && <button className="clear-link" onClick={markRead}>Mark all read</button>}
          </div>
          {items.length === 0 && <div className="muted notif-empty">Nothing in the last 48 hours.</div>}
          <div className="notif-list">
            {items.map((i) => (
              <button key={i.id} className="notif-item" onClick={() => openItem(i)}>
                <span className={`notif-dot ${i.kind}`} />
                <span className="notif-text">
                  <span className={new Date(i.time).getTime() > seen ? "notif-title new" : "notif-title"}>{i.title}</span>
                  <span className="notif-detail">{i.detail}</span>
                </span>
                <span className="notif-time">{timeAgo(i.time)}</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

const SCORING = [
  ["Power is out right now", "+40"],
  ["Each hour without power (up to 20 h)", "+2"],
  ["Indoor temperature below 40°F / 50°F / 60°F", "+25 / +15 / +5"],
  ["Uses a medical device", "+15"],
  ["Asked for a call", "+15"],
  ["Lives alone", "+10"],
  ["Mobility limits", "+10"],
];

export function HelpMenu() {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!open) return;
    const onKey = (e) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open]);

  return (
    <>
      <button className="icon-btn" onClick={() => setOpen(true)} aria-label="Help"><HelpIcon /></button>
      {open && (
        <div className="lightbox" onClick={() => setOpen(false)}>
          <div className="help-panel" role="dialog" aria-label="How Anchor works" onClick={(e) => e.stopPropagation()}>
            <div className="help-head">
              <h2 className="help-title">How Anchor works</h2>
              <button className="btn small" onClick={() => setOpen(false)}>Close</button>
            </div>
            <p className="muted">
              Sensor boxes in customers' homes record power and indoor temperature. When the power goes out,
              Anchor ranks who to call first and helps you start their claim.
            </p>

            <h3>How the call queue ranks homes</h3>
            <table className="help-table">
              <tbody>
                {SCORING.map(([what, pts]) => <tr key={what}><td>{what}</td><td>{pts}</td></tr>)}
              </tbody>
            </table>
            <p className="muted small">Resolved households always move to the bottom.</p>
            <div className="tags">
              <span className="badge sev-critical">70+ Critical</span>
              <span className="badge sev-high">45–69 High</span>
              <span className="badge sev-moderate">20–44 Moderate</span>
              <span className="badge sev-low">Under 20 Low</span>
            </div>

            <h3>Claim drafts</h3>
            <div className="help-sources">
              <div><span className="src src-measured">Measured</span> straight from the box's sensors</div>
              <div><span className="src src-photo">From photo</span> seen by Gemini in a claim photo</div>
              <div><span className="src src-needs_confirmation">Needs confirmation</span> an AI suggestion to check with the customer</div>
            </div>
            <p className="muted small">Nothing is filed until you approve the draft. You can edit any field first.</p>

            <h3>Evidence integrity</h3>
            <p className="muted small">
              Every reading is chained to the one before it with a SHA-256 hash, and every message from a box is
              signed. Changed readings show as Tampered, and fake or replayed messages are blocked and logged.
              Photos show Verified while they still match the hash saved at upload.
            </p>

            <h3>Live box vs simulated</h3>
            <p className="muted small">
              The red ● Live box tag marks the real hardware. The other households are simulated so the
              dashboard shows a full outage.
            </p>
          </div>
        </div>
      )}
    </>
  );
}
