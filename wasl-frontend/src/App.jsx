import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  ask as apiAsk,
  deleteDocument,
  getHealth,
  listDocuments,
  listShipments,
  startInvestigation,
  decideInvestigation,
  uploadDocument,
} from "./api.js";

const C = {
  navy: "#06264a",
  navy2: "#0b315b",
  amber: "#f2aa00",
  amberSoft: "#fff7e5",
  bg: "#faf9f6",
  card: "#ffffff",
  text: "#11233b",
  text2: "#3c4c60",
  muted: "#78879a",
  faint: "#9aa6b5",
  border: "#e8e5de",
  border2: "#f0eee9",
  green: "#20905a",
  greenSoft: "#eaf7ef",
  red: "#d74d4d",
  redSoft: "#fdeeee",
  blue: "#3173c8",
  blueSoft: "#eaf2ff",
};

const SVG = ({ children, size = 18, strokeWidth = 1.8, ...props }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth={strokeWidth}
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
    {...props}
  >
    {children}
  </svg>
);

const Icons = {
  home: (p) => <SVG {...p}><path d="M3 10.5 12 3l9 7.5"/><path d="M5 9.5V21h14V9.5"/><path d="M9 21v-7h6v7"/></SVG>,
  chat: (p) => <SVG {...p}><path d="M21 15a4 4 0 0 1-4 4H8l-5 3 1.7-5A8 8 0 1 1 21 15Z"/></SVG>,
  search: (p) => <SVG {...p}><circle cx="11" cy="11" r="7"/><path d="m20 20-3.6-3.6"/></SVG>,
  fileSearch: (p) => <SVG {...p}><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h8"/><path d="M14 2v6h6"/><circle cx="17" cy="17" r="3"/><path d="m19.3 19.3 2 2"/></SVG>,
  book: (p) => <SVG {...p}><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2Z"/></SVG>,
  gear: (p) => <SVG {...p}><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1-2.8 2.8-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.6V21h-4v-.1a1.7 1.7 0 0 0-1-1.6 1.7 1.7 0 0 0-1.9.3l-.1.1L4.2 17l.1-.1a1.7 1.7 0 0 0 .3-1.9 1.7 1.7 0 0 0-1.6-1H3v-4h.1a1.7 1.7 0 0 0 1.6-1 1.7 1.7 0 0 0-.3-1.9l-.1-.1L7 4.2l.1.1a1.7 1.7 0 0 0 1.9.3 1.7 1.7 0 0 0 1-1.6V3h4v.1a1.7 1.7 0 0 0 1 1.6 1.7 1.7 0 0 0 1.9-.3l.1-.1L19.8 7l-.1.1a1.7 1.7 0 0 0-.3 1.9 1.7 1.7 0 0 0 1.6 1h.1v4H21a1.7 1.7 0 0 0-1.6 1Z"/></SVG>,
  database: (p) => <SVG {...p}><ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v6c0 1.7 3.6 3 8 3s8-1.3 8-3V5"/><path d="M4 11v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6"/></SVG>,
  box: (p) => <SVG {...p}><path d="m21 8-9 5-9-5"/><path d="m3 8 9-5 9 5v8l-9 5-9-5Z"/><path d="M12 13v8"/></SVG>,
  alert: (p) => <SVG {...p}><path d="M10.3 3.5 2.4 17.2A2 2 0 0 0 4.1 20h15.8a2 2 0 0 0 1.7-2.8L13.7 3.5a2 2 0 0 0-3.4 0Z"/><path d="M12 9v4"/><path d="M12 17h.01"/></SVG>,
  calendar: (p) => <SVG {...p}><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M16 3v4M8 3v4M3 10h18"/><circle cx="16.5" cy="16.5" r="2.5"/></SVG>,
  upload: (p) => <SVG {...p}><path d="M12 16V4"/><path d="m7 9 5-5 5 5"/><path d="M5 20h14"/></SVG>,
  trash: (p) => <SVG {...p}><path d="M3 6h18"/><path d="M8 6V4h8v2"/><path d="M19 6l-1 15H6L5 6"/><path d="M10 11v6M14 11v6"/></SVG>,
  send: (p) => <SVG {...p}><path d="m22 2-7 20-4-9-9-4Z"/><path d="M22 2 11 13"/></SVG>,
  logout: (p) => <SVG {...p}><path d="M10 17l5-5-5-5"/><path d="M15 12H3"/><path d="M14 3h5a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-5"/></SVG>,
  lock: (p) => <SVG {...p}><rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/></SVG>,
  chevron: (p) => <SVG {...p}><path d="m9 18 6-6-6-6"/></SVG>,
  close: (p) => <SVG {...p}><path d="M18 6 6 18M6 6l12 12"/></SVG>,
  left: (p) => <SVG {...p}><path d="m15 18-6-6 6-6"/></SVG>,
  right: (p) => <SVG {...p}><path d="m9 18 6-6-6-6"/></SVG>,
  copy: (p) => <SVG {...p}><rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></SVG>,
  check: (p) => <SVG {...p}><path d="m5 12 4 4L19 6"/></SVG>,
};

function nowTime() {
  return new Date().toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
}

function docType(name = "") {
  const ext = name.split(".").pop()?.toLowerCase();
  if (ext === "pdf") return { label: "PDF", color: "#dc4343", bg: "#fdecec" };
  if (ext === "md") return { label: "MD", color: "#536579", bg: "#eef1f4" };
  if (ext === "txt") return { label: "TXT", color: "#536579", bg: "#eef1f4" };
  return { label: "DOC", color: "#2d69c0", bg: "#eaf2ff" };
}

function dedupeSources(items = []) {
  const seen = new Set();
  return items.filter((c) => {
    if (!c?.source || seen.has(c.source)) return false;
    seen.add(c.source);
    return true;
  });
}

function compactHistoryText(value, maxLength = 1200) {
  const text = String(value || "").trim();

  if (text.length <= maxLength) {
    return text;
  }

  const separator = "\n...\n";
  const remaining = maxLength - separator.length;
  const startLength = Math.ceil(remaining / 2);
  const endLength = Math.floor(remaining / 2);

  return (
    text.slice(0, startLength) +
    separator +
    text.slice(-endLength)
  );
}

const STATUS_LABELS = {
  pending: "Pending",
  in_transit: "In transit",
  at_customs: "At customs",
  held: "Held",
  out_for_delivery: "Out for delivery",
  delivered: "Delivered",
  failed_delivery: "Failed delivery",
  returned: "Returned",
};

const EXCEPTION_LABELS = {
  none: "Clear",
  customs_hold: "Customs hold",
  holiday_closure: "Holiday closure",
  cross_border: "Cross-border",
  supplier_delay: "Supplier delay",
  carrier_delay: "Carrier delay",
  failed_delivery: "Failed delivery",
};

function prettyStatus(value) {
  return STATUS_LABELS[value] || value || "—";
}

function prettyException(value) {
  return EXCEPTION_LABELS[value] || value || "—";
}

function SlaBadge({ status }) {
  if (status === "breached") {
    return <span className="sla-badge sla-breached">Breached</span>;
  }
  if (status === "at_risk") {
    return <span className="sla-badge sla-risk">At Risk</span>;
  }
  return <span className="sla-badge sla-ok">OK</span>;
}

function ExceptionBadge({ value }) {
  if (!value || value === "none") {
    return <span className="exception-badge exception-clear">Clear</span>;
  }

  const danger = ["customs_hold", "failed_delivery"].includes(value);
  const warning = ["supplier_delay", "carrier_delay", "holiday_closure"].includes(value);

  return (
    <span
      className={`exception-badge ${
        danger ? "exception-danger" : warning ? "exception-warning" : "exception-info"
      }`}
    >
      {prettyException(value)}
    </span>
  );
}

function formatDateTime(value) {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleString([], {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function formatSar(value, { emptyZero = true } = {}) {
  const n = Number(value || 0);
  if (!Number.isFinite(n) || (emptyZero && n <= 0)) return "—";
  return `SAR ${n.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
}

function formatSlaTime(hours, status) {
  if (hours === null || hours === undefined || Number.isNaN(Number(hours))) {
    return status === "breached" ? "Breached" : "—";
  }

  const n = Number(hours);
  const abs = Math.abs(n);
  const rounded = Math.max(1, Math.round(abs));

  if (status === "breached" || n < 0) {
    if (rounded < 24) return `Breached by ${rounded}h`;
    const days = Math.floor(rounded / 24);
    const remainder = rounded % 24;
    return remainder ? `Breached by ${days}d ${remainder}h` : `Breached by ${days}d`;
  }

  if (rounded < 24) return `${rounded}h remaining`;
  const days = Math.floor(rounded / 24);
  const remainder = rounded % 24;
  return remainder ? `${days}d ${remainder}h remaining` : `${days}d remaining`;
}

function priorityRank(shipment) {
  if (shipment.sla_status === "breached") return 0;
  if (shipment.sla_status === "at_risk") return 1;
  if (shipment.exception_type && shipment.exception_type !== "none") return 2;
  return 3;
}

function DetailField({ label, value, mono = false }) {
  return (
    <div className="detail-field">
      <span className="detail-label">{label}</span>
      <span className={`detail-value ${mono ? "detail-mono" : ""}`}>{value || "—"}</span>
    </div>
  );
}

export default function App() {
  const [nav, setNav] = useState("ask");
  const [online, setOnline] = useState(null);
  const [shipments, setShipments] = useState([]);
  const [docs, setDocs] = useState({ documents: [], count: 0, total_chunks: 0 });
  const [investigationTargetId, setInvestigationTargetId] = useState("");

  async function refresh() {
    const [h, s, d] = await Promise.allSettled([
      getHealth(),
      listShipments(),
      listDocuments(),
    ]);
    setOnline(h.status === "fulfilled");
    if (s.status === "fulfilled") setShipments(Array.isArray(s.value) ? s.value : []);
    if (d.status === "fulfilled") setDocs(d.value || { documents: [], count: 0, total_chunks: 0 });
  }

  useEffect(() => { refresh(); }, []);

  const metrics = useMemo(() => {
    const active = shipments.filter((s) => s.status !== "delivered");
    const breached = active.filter((s) => s.sla_status === "breached");
    const atRisk = active.filter((s) => s.sla_status === "at_risk");
    const high = active.filter((s) => Number(s.shipment_value_sar || 0) >= 500000);
    const exceptions = active.filter((s) => s.exception_type && s.exception_type !== "none");
    return {
      active: active.length,
      breached: breached.length,
      atRisk: atRisk.length,
      high: high.length,
      exceptions: exceptions.length,
    };
  }, [shipments]);

  function navigate(next) {
    if (next === "investigations") {
      setInvestigationTargetId("");
    }
    setNav(next);
  }

  function openInvestigation(shipmentId) {
    setInvestigationTargetId(shipmentId);
    setNav("investigations");
  }

  return (
    <div className="app">
      <Styles />
      <Sidebar nav={nav} onNav={navigate} />
      <section className="main">
        <Header nav={nav} online={online} />
        {nav === "ask" && (
          <AskPage
            docs={docs}
            shipments={shipments}
            metrics={metrics}
            refresh={refresh}
          />
        )}
        {nav === "dashboard" && (
          <Dashboard
            shipments={shipments}
            metrics={metrics}
            onOpenInvestigation={openInvestigation}
          />
        )}
        {nav === "investigations" && (
          <Investigations
            shipments={shipments}
            initialShipmentId={investigationTargetId}
            onInitialHandled={() => setInvestigationTargetId("")}
          />
        )}
        {nav === "docs" && <DocumentsPage docs={docs} refresh={refresh} />}
        {nav === "settings" && <Settings />}
      </section>
    </div>
  );
}

function Styles() {
  return <style>{`
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=IBM+Plex+Mono:wght@500;600&display=swap');

    :root{
      font-family:Inter,system-ui,sans-serif;
      color:${C.text};
      background:${C.bg};
    }
    *{box-sizing:border-box}
    html,body,#root{margin:0;min-height:100%}
    body{background:${C.bg};font-size:13px}
    button,input,textarea{font:inherit}
    button{cursor:pointer}
    button:disabled{opacity:.55;cursor:not-allowed}
    .app{min-height:100vh;display:flex;background:${C.bg}}
    .main{flex:1;min-width:0}
    .sidebar{
      width:228px;
      min-height:100vh;
      position:sticky;
      top:0;
      flex-shrink:0;
      background:linear-gradient(180deg,#06284d 0%,#052443 100%);
      color:white;
      display:flex;
      flex-direction:column;
    }
    .brand{
      height:76px;
      display:flex;
      align-items:center;
      padding:0 22px;
      gap:10px;
    }
    .mark{
      font-size:25px;
      font-weight:800;
      font-style:italic;
      letter-spacing:-5px;
      color:${C.amber};
      width:30px;
    }
    .brand-name{font-size:24px;line-height:1;font-weight:700;letter-spacing:-.6px}
    .brand-sub{font-size:8.5px;color:${C.amber};font-weight:700;margin-top:4px;letter-spacing:.4px}
    .side-nav{padding:23px 9px;flex:1}
    .side-button{
      position:relative;
      display:flex;
      width:100%;
      height:46px;
      border:0;
      border-radius:8px;
      align-items:center;
      gap:13px;
      padding:0 14px;
      margin:3px 0;
      background:transparent;
      color:#e8eff5;
      font-weight:500;
      font-size:13px;
      text-align:left;
    }
    .side-button:hover{background:rgba(255,255,255,.06)}
    .side-button.active{background:#173f6b;color:${C.amber};font-weight:600}
    .side-button.active:before{
      content:"";
      position:absolute;
      left:0;
      top:7px;
      bottom:7px;
      width:3px;
      border-radius:0 2px 2px 0;
      background:${C.amber};
    }
    .side-icon{display:grid;place-items:center;width:20px;color:#dbe7f1}
    .side-button.active .side-icon{color:${C.amber}}
    .profile{
      margin:0 17px 14px;
      border-top:1px solid rgba(255,255,255,.15);
      padding:15px 3px 0;
      display:flex;
      gap:10px;
      align-items:center;
    }
    .profile-avatar{
      width:38px;height:38px;border:1px solid ${C.amber};border-radius:50%;
      display:grid;place-items:center;color:${C.amber};font-weight:700;font-size:12px
    }
    .profile-name{font-size:12px;font-weight:600}
    .profile-role{font-size:10px;color:#c8d5e1;margin-top:3px}
    .header{
      height:58px;
      padding:0 28px;
      border-bottom:1px solid ${C.border};
      background:rgba(255,255,255,.86);
      backdrop-filter:blur(10px);
      display:flex;
      justify-content:space-between;
      gap:22px;
      align-items:center;
      position:sticky;
      top:0;
      z-index:10;
    }
    .page-title{font-size:20px;font-weight:700;letter-spacing:-.4px;margin:0}
    .live{display:flex;align-items:center;gap:7px;color:${C.muted};font-size:11px}
    .live-dot{width:7px;height:7px;border-radius:50%}

    .ask-page{padding:10px 26px 22px}
    .session-row{height:38px;display:flex;align-items:center;justify-content:flex-end;gap:10px}
    .session-pill{
      display:flex;align-items:center;gap:7px;
      height:31px;padding:0 12px;border-radius:10px;
      background:${C.amberSoft};color:#8f6205;
      font-size:10px;font-weight:600
    }
    .quit{
      display:flex;align-items:center;gap:7px;
      height:31px;padding:0 12px;border-radius:8px;
      background:#fff;color:${C.text};
      border:1px solid #aeb8c3;font-size:10px;font-weight:600
    }
    .metrics{
      display:grid;
      grid-template-columns:repeat(4,minmax(0,1fr));
      gap:12px;
      margin:8px 0 12px;
    }
    .metric{
      height:82px;
      border:1px solid ${C.border};
      background:#fff;
      border-radius:12px;
      padding:12px 13px;
      display:flex;
      align-items:center;
      gap:11px;
      box-shadow:0 1px 6px rgba(16,28,42,.02);
      min-width:0;
    }
    .metric-icon{
      width:40px;height:40px;border-radius:10px;
      display:grid;place-items:center;flex-shrink:0
    }
    .metric-title{font-size:10px;font-weight:600;color:${C.text2};white-space:nowrap}
    .metric-value{font-size:17px;line-height:1.15;font-weight:700;margin-top:2px}
    .metric-detail{
      font-size:9.5px;color:${C.muted};margin-top:4px;
      white-space:nowrap;overflow:hidden;text-overflow:ellipsis
    }

    .workspace{
      display:grid;
      grid-template-columns:minmax(0,1fr) 382px;
      gap:14px;
      align-items:start;
    }
    .chat-card{
      height:calc(100vh - 204px);
      min-height:590px;
      background:#fff;
      border:1px solid ${C.border};
      border-radius:12px;
      overflow:hidden;
      display:flex;
      flex-direction:column;
    }
    .day{
      height:34px;
      padding:0 15px;
      display:flex;align-items:center;gap:12px;
      font-size:9px;color:${C.faint}
    }
    .day:before,.day:after{content:"";height:1px;background:${C.border2};flex:1}
    .messages{
      flex:1;
      min-height:0;
      overflow-y:auto;
      padding:2px 14px 12px;
    }
    .empty{
      min-height:100%;
      display:flex;
      align-items:center;
      justify-content:center;
      color:${C.muted};
      text-align:center;
    }
    .empty-inner{max-width:380px;transform:translateY(-14px)}
    .empty-logo{
      width:36px;height:36px;border-radius:50%;background:${C.navy};
      color:${C.amber};display:grid;place-items:center;margin:0 auto 10px;
      font-size:12px;font-weight:800
    }
    .empty-title{font-size:14px;font-weight:650;color:${C.text};margin-bottom:4px}
    .empty-copy{font-size:10.5px;line-height:1.55}
    .user-wrap{display:flex;justify-content:flex-end;align-items:flex-end;gap:6px;margin:8px 0 13px}
    .time{font-size:8.5px;color:${C.faint};margin-bottom:4px}
    .user-time{text-align:right}
    .user-msg{
      max-width:490px;background:#dcecff;color:${C.text};
      border-radius:9px 9px 3px 9px;padding:9px 12px;
      font-size:10.5px;line-height:1.5
    }
    .ticks{font-size:9px;color:#1473e6;margin-bottom:4px}
    .assistant-wrap{display:flex;align-items:flex-start;gap:8px;margin:8px 0 14px}
    .bot{
      width:30px;height:30px;border-radius:50%;background:${C.navy};color:${C.amber};
      display:grid;place-items:center;font-size:10px;font-weight:800;flex-shrink:0;margin-top:14px
    }
    .assistant-col{max-width:76%;min-width:0}
    .assistant-msg{
      border:1px solid ${C.border};
      border-radius:3px 9px 9px 9px;
      padding:10px 12px;
      background:#fff;
      font-size:10.5px;
      line-height:1.5;
      box-shadow:0 1px 4px rgba(20,31,45,.025)
    }
    .answer-p{margin:0 0 6px}
    .answer-ul{margin:4px 0 7px;padding-left:17px}
    .answer-h2{font-size:13px;margin:2px 0 6px}
    .answer-h3{font-size:11.5px;margin:7px 0 4px}
    .answer-h4{font-size:10.5px;margin:6px 0 3px}
    .ungrounded{
      display:inline-block;padding:3px 6px;background:${C.amberSoft};color:#8d6207;
      border-radius:5px;font-size:8px;font-weight:700;letter-spacing:.5px;text-transform:uppercase;margin-bottom:7px
    }
    .sources{border-top:1px solid ${C.border2};margin-top:8px;padding-top:7px}
    .sources-title{font-size:8.5px;font-weight:700;margin-bottom:5px}
    .chips{display:flex;gap:5px;flex-wrap:wrap}
    .source-chip{
      max-width:220px;display:flex;gap:6px;align-items:center;
      border:1px solid ${C.border};border-radius:7px;background:#fcfbf8;padding:5px 6px
    }
    .file-badge{
      width:22px;height:22px;border-radius:5px;display:grid;place-items:center;
      font-size:7px;font-weight:800;flex-shrink:0
    }
    .source-name{font-size:8px;font-weight:650;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
    .source-meta{font-size:7.5px;color:${C.muted};margin-top:1px}
    .composer{
      margin:0 12px 11px;
      min-height:46px;
      border:1px solid ${C.border};
      border-radius:10px;
      display:flex;align-items:center;gap:7px;padding:5px 6px;
      background:#fff
    }
    .composer textarea{
      flex:1;resize:none;border:0;outline:0;color:${C.text};
      min-height:30px;max-height:72px;padding:7px 4px;font-size:10.5px
    }
    .send{
      width:34px;height:34px;border:0;border-radius:8px;
      display:grid;place-items:center;background:${C.navy};color:white
    }
    .error{
      margin:0 12px 7px;background:${C.redSoft};color:${C.red};
      border-radius:7px;padding:7px 10px;font-size:9.5px
    }

    .right{min-width:0}
    .kb{
      background:#fff;border:1px solid ${C.border};border-radius:12px;overflow:hidden
    }
    .kb-header{
      height:54px;display:flex;align-items:center;justify-content:space-between;
      padding:0 14px;border-bottom:1px solid ${C.border2}
    }
    .kb-title{font-size:12.5px;font-weight:700}
    .upload{
      height:30px;padding:0 10px;display:flex;align-items:center;gap:6px;
      border:0;border-radius:7px;background:${C.navy};color:white;
      font-size:9px;font-weight:600
    }
    .kb-cols,.kb-row{
      display:grid;grid-template-columns:minmax(0,1fr) 55px 64px 24px;
      align-items:center;gap:7px;padding:0 13px
    }
    .kb-cols{
      height:32px;border-bottom:1px solid ${C.border2};
      font-size:8px;color:${C.muted};font-weight:600
    }
    .kb-list{max-height:478px;overflow-y:auto}
    .kb-row{
      min-height:39px;border-bottom:1px solid ${C.border2};
      font-size:8.5px
    }
    .kb-row:hover{background:#faf9f6}
    .doc-cell{display:flex;align-items:center;gap:6px;min-width:0}
    .doc-name{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-weight:550}
    .tiny-file{
      width:19px;height:19px;border-radius:4px;display:grid;place-items:center;
      font-size:6px;font-weight:800;flex-shrink:0
    }
    .status{
      display:inline-block;background:${C.greenSoft};color:${C.green};
      border-radius:5px;padding:3px 5px;font-size:7px;font-weight:700
    }
    .trash{border:0;background:transparent;color:#8895a5;padding:3px;display:grid;place-items:center}
    .kb-empty{height:150px;display:grid;place-items:center;color:${C.muted};font-size:9.5px}
    .kb-footer{height:30px;display:flex;align-items:center;padding:0 13px;color:${C.muted};font-size:8px}
    .kb-error{margin:8px;background:${C.redSoft};color:${C.red};border-radius:6px;padding:7px;font-size:8px}
    .history-note{
      margin-top:10px;min-height:38px;border-radius:10px;background:${C.amberSoft};
      color:#8c6006;display:flex;align-items:center;gap:7px;padding:0 13px;font-size:9px
    }
    .context{margin-top:10px}
    .context-body{padding:5px 13px 10px}
    .context-row{
      min-height:29px;display:flex;justify-content:space-between;align-items:center;
      gap:10px;border-bottom:1px solid ${C.border2};font-size:8.5px
    }
    .context-label{color:${C.muted}}
    .context-value{text-align:right;font-weight:500}

    .simple-page{padding:24px 28px}
    .table-card{background:#fff;border:1px solid ${C.border};border-radius:12px;overflow:hidden}
    .table-head{height:50px;padding:0 16px;display:flex;align-items:center;font-size:13px;font-weight:700;border-bottom:1px solid ${C.border2}}

    .sla-badge,.exception-badge{
      display:inline-flex;
      align-items:center;
      width:max-content;
      border-radius:6px;
      padding:4px 7px;
      font-size:8px;
      font-weight:700;
      line-height:1;
      white-space:nowrap;
    }
    .sla-breached{background:#fdecec;color:#c83f3f;border:1px solid #f5caca}
    .sla-risk{background:#fff5df;color:#b97700;border:1px solid #f3dfad}
    .sla-ok{background:#eaf7ef;color:#208858;border:1px solid #cfe9d9}
    .exception-clear{background:#eef6f1;color:#47735b}
    .exception-danger{background:#fdecec;color:#c83f3f}
    .exception-warning{background:#fff5df;color:#a96f00}
    .exception-info{background:#edf2fa;color:#426a9a}

    .dashboard-toolbar{
      min-height:52px;
      padding:8px 14px;
      display:flex;
      align-items:center;
      justify-content:space-between;
      gap:12px;
      border-bottom:1px solid ${C.border2};
      background:#fff;
    }
    .dashboard-toolbar-copy{min-width:0}
    .dashboard-toolbar-title{font-size:12px;font-weight:700}
    .dashboard-toolbar-sub{font-size:8.5px;color:${C.muted};margin-top:3px}
    .dashboard-filters{display:flex;align-items:center;gap:5px;flex-wrap:wrap;justify-content:flex-end}
    .filter-chip{
      height:28px;
      border:1px solid ${C.border};
      background:#fff;
      color:${C.text2};
      border-radius:8px;
      padding:0 9px;
      font-size:8.5px;
      font-weight:600;
    }
    .filter-chip:hover{background:#faf9f6;border-color:#d8d2c7}
    .filter-chip.active{
      color:${C.navy};
      background:${C.amberSoft};
      border-color:#ead393;
      box-shadow:inset 0 0 0 1px rgba(242,170,0,.08);
    }

    .dashboard-head,.dashboard-row{
      display:grid;
      grid-template-columns:1.05fr 1.55fr .9fr 1.05fr .95fr .9fr 22px;
      align-items:center;
      gap:10px;
      padding:0 16px;
    }
    .dashboard-head{
      min-height:34px;
      color:${C.muted};
      font-size:8px;
      font-weight:700;
      text-transform:uppercase;
      letter-spacing:.35px;
      border-bottom:1px solid ${C.border2};
      background:#fcfbf8;
    }
    .dashboard-row{
      width:100%;
      min-height:50px;
      border:0;
      border-bottom:1px solid ${C.border2};
      background:#fff;
      color:${C.text};
      font-size:9px;
      text-align:left;
      cursor:pointer;
      transition:background .12s,box-shadow .12s,transform .08s;
    }
    .dashboard-row:hover{
      background:#fffdf8;
      box-shadow:inset 3px 0 0 ${C.amber};
    }
    .dashboard-row:focus-visible{
      outline:2px solid #7ba9df;
      outline-offset:-2px;
      background:#f7fbff;
    }
    .dashboard-row.selected{
      background:#fffaf0;
      box-shadow:inset 3px 0 0 ${C.amber};
    }
    .row-chevron{color:${C.faint};display:grid;place-items:center}
    .dashboard-row:hover .row-chevron{color:${C.navy};transform:translateX(1px)}
    .dashboard-empty{
      min-height:120px;
      display:grid;
      place-items:center;
      color:${C.muted};
      font-size:10px;
    }

    .drawer-backdrop{
      position:fixed;
      inset:0;
      z-index:40;
      background:rgba(5,23,43,.22);
      backdrop-filter:blur(1.5px);
      animation:fadeBackdrop .16s ease-out;
    }
    .shipment-drawer{
      position:fixed;
      z-index:41;
      top:0;
      right:0;
      height:100dvh;
      width:min(470px,92vw);
      background:#fff;
      border-left:1px solid ${C.border};
      box-shadow:-16px 0 42px rgba(6,38,74,.15);
      display:flex;
      flex-direction:column;
      animation:drawerIn .2s ease-out;
    }
    @keyframes fadeBackdrop{from{opacity:0}to{opacity:1}}
    @keyframes drawerIn{from{transform:translateX(22px);opacity:.55}to{transform:translateX(0);opacity:1}}

    .drawer-head{
      flex-shrink:0;
      padding:16px 18px 14px;
      border-bottom:1px solid ${C.border};
      background:linear-gradient(180deg,#fff 0%,#fdfcf9 100%);
    }
    .drawer-head-top{display:flex;align-items:center;justify-content:space-between;gap:12px}
    .drawer-eyebrow{
      font-size:8px;
      font-weight:700;
      letter-spacing:.65px;
      color:${C.muted};
      text-transform:uppercase;
    }
    .drawer-id-row{display:flex;align-items:center;gap:8px;margin-top:5px;min-width:0}
    .drawer-id{
      font-family:"IBM Plex Mono",monospace;
      font-size:14px;
      font-weight:600;
      color:${C.navy};
      white-space:nowrap;
      overflow:hidden;
      text-overflow:ellipsis;
    }
    .drawer-icon-btn{
      width:30px;height:30px;display:grid;place-items:center;
      border:1px solid ${C.border};border-radius:8px;background:#fff;color:${C.text2};
      flex-shrink:0;
    }
    .drawer-icon-btn:hover{background:#f7f6f2;color:${C.navy}}
    .drawer-head-actions{display:flex;gap:6px}
    .drawer-summary{display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin-top:11px}
    .high-value-badge{
      display:inline-flex;align-items:center;height:22px;padding:0 7px;border-radius:6px;
      background:${C.amberSoft};color:#996800;font-size:7.5px;font-weight:700;
      border:1px solid #f0d99c;
    }

    .drawer-body{
      flex:1;
      min-height:0;
      overflow-y:auto;
      padding:15px 18px 22px;
      overscroll-behavior:contain;
    }
    .drawer-route{
      padding:13px 14px;
      border-radius:11px;
      background:#f7f9fc;
      border:1px solid #e7ecf2;
      margin-bottom:14px;
    }
    .route-main{font-size:11px;font-weight:650;color:${C.text};line-height:1.45}
    .route-current{font-size:8.5px;color:${C.muted};margin-top:5px;line-height:1.45}
    .drawer-section{
      margin-top:14px;
      padding-top:14px;
      border-top:1px solid ${C.border2};
    }
    .drawer-section:first-of-type{margin-top:0}
    .drawer-section-title{
      font-size:8px;
      font-weight:800;
      letter-spacing:.55px;
      color:${C.muted};
      text-transform:uppercase;
      margin-bottom:8px;
    }
    .detail-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}
    .detail-field{
      min-width:0;
      padding:9px 10px;
      border:1px solid ${C.border2};
      border-radius:9px;
      background:#fff;
    }
    .detail-label{
      display:block;
      color:${C.muted};
      font-size:7.5px;
      margin-bottom:4px;
    }
    .detail-value{
      display:block;
      color:${C.text};
      font-size:9px;
      font-weight:600;
      line-height:1.4;
      overflow-wrap:anywhere;
    }
    .detail-mono{font-family:"IBM Plex Mono",monospace;font-size:8.5px}
    .detail-callout{
      border-radius:10px;
      padding:11px 12px;
      font-size:9px;
      line-height:1.55;
    }
    .detail-callout.danger{
      background:#fff6f6;
      border:1px solid #f5d5d5;
      color:#7f3333;
    }
    .detail-callout.neutral{
      background:#f8f8f6;
      border:1px solid ${C.border};
      color:${C.text2};
    }
    .drawer-footer{
      flex-shrink:0;
      min-height:64px;
      padding:10px 14px;
      border-top:1px solid ${C.border};
      background:#fff;
      display:flex;
      align-items:center;
      justify-content:space-between;
      gap:10px;
    }
    .drawer-nav{display:flex;align-items:center;gap:6px}
    .drawer-nav-label{font-size:8px;color:${C.muted};min-width:42px;text-align:center}
    .investigate-btn{
      min-height:36px;
      padding:0 14px;
      border:0;
      border-radius:9px;
      background:${C.navy};
      color:#fff;
      font-size:9px;
      font-weight:700;
      display:flex;
      align-items:center;
      gap:7px;
    }
    .investigate-btn:hover{background:${C.navy2}}
    .investigation-layout{
      display:grid;
      grid-template-columns:1fr;
      gap:14px;
      align-items:start;
    }
    .investigation-layout.with-panel{
      grid-template-columns:minmax(360px,.92fr) minmax(420px,1.08fr);
    }
    .investigation-queue,.investigation-panel{
      background:#fff;
      border:1px solid ${C.border};
      border-radius:12px;
      overflow:hidden;
      box-shadow:0 1px 2px rgba(6,38,74,.02);
    }
    .investigation-queue-head{
      min-height:54px;
      padding:10px 14px;
      display:flex;
      align-items:center;
      justify-content:space-between;
      gap:10px;
      border-bottom:1px solid ${C.border2};
    }
    .investigation-queue-title{font-size:12px;font-weight:700}
    .investigation-queue-sub{font-size:8px;color:${C.muted};margin-top:3px}
    .investigation-count{
      display:inline-flex;align-items:center;justify-content:center;
      min-width:24px;height:22px;border-radius:999px;
      background:#f2f3f4;color:${C.text2};font-size:8px;font-weight:700;padding:0 7px;
    }
    .investigation-head,.investigation-row{
      display:grid;
      grid-template-columns:1.15fr 1.15fr .8fr 18px;
      align-items:center;
      gap:9px;
      padding:0 13px;
    }
    .investigation-head{
      min-height:34px;
      color:${C.muted};
      font-size:7.5px;
      font-weight:700;
      text-transform:uppercase;
      letter-spacing:.35px;
      border-bottom:1px solid ${C.border2};
      background:#fcfbf8;
    }
    .investigation-row{
      width:100%;
      min-height:52px;
      border:0;
      border-bottom:1px solid ${C.border2};
      background:#fff;
      color:${C.text};
      font-size:8.5px;
      text-align:left;
      cursor:pointer;
      transition:background .12s,box-shadow .12s;
    }
    .investigation-row:hover{
      background:#fffdf8;
      box-shadow:inset 3px 0 0 ${C.amber};
    }
    .investigation-row.selected{
      background:#fff9ec;
      box-shadow:inset 3px 0 0 ${C.amber};
    }
    .investigation-route{
      display:block;
      margin-top:3px;
      color:${C.muted};
      font-size:7.5px;
      white-space:nowrap;
      overflow:hidden;
      text-overflow:ellipsis;
    }
    .investigation-chevron{color:${C.faint};display:grid;place-items:center}
    .investigation-panel-head{
      min-height:66px;
      padding:13px 15px;
      display:flex;
      align-items:flex-start;
      justify-content:space-between;
      gap:12px;
      border-bottom:1px solid ${C.border2};
      background:linear-gradient(180deg,#fff 0%,#fdfcf9 100%);
    }
    .investigation-panel-id{
      font-family:"IBM Plex Mono",monospace;
      font-size:12px;
      font-weight:650;
      color:${C.navy};
    }
    .investigation-panel-route{
      margin-top:4px;
      font-size:8px;
      color:${C.muted};
      line-height:1.4;
    }
    .investigation-panel-body{padding:14px}
    .investigation-empty{
      min-height:410px;
      display:grid;
      place-items:center;
      text-align:center;
      padding:30px;
      color:${C.muted};
    }
    .investigation-empty-icon{
      width:44px;height:44px;border-radius:12px;background:#f2f4f6;
      display:grid;place-items:center;color:${C.navy};margin:0 auto 10px;
    }
    .investigation-empty-title{font-size:11px;font-weight:700;color:${C.text}}
    .investigation-empty-copy{font-size:8.5px;line-height:1.55;margin-top:5px;max-width:280px}
    .investigation-run{
      margin-top:13px;
      min-height:36px;
      border:0;
      border-radius:9px;
      padding:0 13px;
      background:${C.navy};
      color:#fff;
      font-size:9px;
      font-weight:700;
      display:inline-flex;
      align-items:center;
      gap:7px;
    }
    .investigation-run:hover{background:${C.navy2}}
    .agent-loading{
      min-height:300px;
      display:grid;
      place-items:center;
      text-align:center;
      color:${C.muted};
      padding:30px;
    }
    .agent-spinner{
      width:25px;height:25px;border-radius:50%;
      border:2px solid #e8ebef;border-top-color:${C.amber};
      animation:agentSpin .7s linear infinite;
      margin:0 auto 10px;
    }
    @keyframes agentSpin{to{transform:rotate(360deg)}}
    .agent-steps{font-size:8px;color:${C.faint};margin-top:5px}
    .agent-error{
      padding:11px 12px;border-radius:9px;background:${C.redSoft};
      border:1px solid #f1cdcd;color:#a23838;font-size:9px;line-height:1.5;
    }
    .agent-section{margin-top:14px;padding-top:14px;border-top:1px solid ${C.border2}}
    .agent-section:first-child{margin-top:0;padding-top:0;border-top:0}
    .agent-section-title{
      font-size:7.5px;font-weight:800;letter-spacing:.55px;
      color:${C.muted};text-transform:uppercase;margin-bottom:8px;
    }
    .agent-trace{
      border-radius:10px;background:${C.navy};padding:11px 12px;
    }
    .agent-trace-row{
      display:grid;grid-template-columns:7px 95px 1fr;
      gap:8px;align-items:start;padding:5px 0;
    }
    .agent-trace-dot{
      width:6px;height:6px;border-radius:50%;background:${C.amber};margin-top:3px;
    }
    .agent-trace-node{
      font-family:"IBM Plex Mono",monospace;font-size:7.5px;color:#9eb0c2;
    }
    .agent-trace-detail{font-size:8px;color:#e0e8ef;line-height:1.45}
    .assessment-card{
      border:1px solid ${C.border};border-radius:10px;padding:11px 12px;background:#fff;
    }
    .assessment-top{display:flex;align-items:center;justify-content:space-between;gap:10px}
    .assessment-text{font-size:9px;line-height:1.58;color:${C.text2};margin-top:7px}
    .urgency-badge{
      height:21px;padding:0 7px;border-radius:999px;
      display:inline-flex;align-items:center;font-size:7px;font-weight:800;text-transform:uppercase;
    }
    .urgency-critical{background:${C.redSoft};color:#b33d3d}
    .urgency-warning{background:${C.amberSoft};color:#9c6b00}
    .urgency-normal{background:${C.greenSoft};color:${C.green}}
    .sla-alert{
      margin-top:9px;padding:8px 10px;border-radius:8px;
      font-size:8.5px;font-weight:650;line-height:1.45;
    }
    .sla-alert.danger{background:${C.redSoft};color:#ad3939}
    .sla-alert.warning{background:${C.amberSoft};color:#956400}
    .draft-card{
      border:1px solid ${C.border};border-radius:10px;overflow:hidden;
    }
    .draft-head{
      padding:8px 11px;background:#f8f8f6;border-bottom:1px solid ${C.border2};
      display:flex;align-items:center;justify-content:space-between;gap:10px;
    }
    .draft-label{font-size:7.5px;color:${C.muted};font-weight:800;text-transform:uppercase;letter-spacing:.45px}
    .draft-recipient{font-size:8px;font-weight:700;color:${C.text2}}
    .draft-body{padding:11px 12px}
    .draft-subject{font-family:"IBM Plex Mono",monospace;font-size:8.5px;font-weight:650;margin-bottom:8px}
    .draft-message{font-size:8.7px;line-height:1.58;color:${C.text2};white-space:pre-wrap}
    .approval-note{
      margin-top:10px;padding:8px 10px;border-radius:8px;background:#f6f8fa;
      color:${C.muted};font-size:7.8px;line-height:1.45;
    }
    .approval-actions{display:flex;gap:8px;margin-top:10px}
    .approve-btn,.reject-btn{
      flex:1;min-height:36px;border-radius:9px;font-size:9px;font-weight:700;
    }
    .approve-btn{border:0;background:${C.green};color:#fff}
    .reject-btn{border:1px solid ${C.border};background:#fff;color:${C.red}}
    .decision-banner{
      margin-top:10px;padding:10px 11px;border-radius:9px;font-size:8.5px;font-weight:700;
      display:flex;align-items:center;gap:7px;
    }
    .decision-banner.approved{background:${C.greenSoft};color:${C.green}}
    .decision-banner.rejected{background:${C.redSoft};color:${C.red}}
    .resolved-card{
      padding:12px;border-radius:10px;border-left:3px solid ${C.green};
      background:${C.greenSoft};font-size:9px;line-height:1.55;color:#355b47;
    }
    .shipment-row{
      min-height:42px;display:grid;grid-template-columns:1.1fr 1.8fr 1fr 1fr;
      align-items:center;gap:12px;padding:0 16px;border-bottom:1px solid ${C.border2};font-size:9.5px
    }

    ::-webkit-scrollbar{width:7px;height:7px}
    ::-webkit-scrollbar-thumb{background:#d8d4cc;border-radius:8px}

    @media(max-width:1200px){
      .workspace{grid-template-columns:minmax(0,1fr) 330px}
      .metric-detail{font-size:8.5px}
    }

    /* Ask page: focused, responsive chat */
    .clean-ask{
      height:calc(100dvh - 58px);
      min-height:0;
      padding:12px 20px 16px;
      display:flex;
    }
    .chat-card-full{
      width:min(980px,100%);
      height:100%;
      min-height:0;
      margin:0 auto;
      border-radius:12px;
    }
    .chat-top{
      height:54px;
      flex-shrink:0;
      padding:0 15px;
      display:flex;
      align-items:center;
      justify-content:space-between;
      gap:12px;
      border-bottom:1px solid ${C.border2};
      background:#fff;
    }
    .chat-top-title{
      font-size:12.5px;
      font-weight:700;
      color:${C.text};
    }
    .chat-top-subtitle{
      margin-top:2px;
      font-size:8.5px;
      color:${C.muted};
    }
    .chat-quit{
      height:29px;
      flex-shrink:0;
    }
    .full-chat-messages{
      padding:10px 18px 14px;
      overscroll-behavior:contain;
      scroll-behavior:smooth;
    }
    .improved-empty{
      min-height:100%;
      padding:18px 0;
    }
    .suggestion-empty{
      width:100%;
      max-width:600px;
      transform:none;
    }
    .suggestions{
      display:grid;
      grid-template-columns:repeat(2,minmax(0,1fr));
      gap:7px;
      margin-top:18px;
      text-align:left;
    }
    .suggestion{
      min-height:44px;
      border:1px solid ${C.border};
      background:#fff;
      border-radius:9px;
      color:${C.text2};
      display:flex;
      align-items:center;
      justify-content:space-between;
      gap:10px;
      padding:9px 11px;
      font-size:9.5px;
      line-height:1.35;
      text-align:left;
      transition:border-color .12s,background .12s,transform .08s;
    }
    .suggestion:hover{
      border-color:#d7c89e;
      background:#fffdf8;
    }
    .suggestion:active{transform:translateY(1px)}
    .full-composer{
      flex-shrink:0;
      margin:0 12px 8px;
    }
    .session-footer{
      flex-shrink:0;
      height:22px;
      display:flex;
      align-items:center;
      justify-content:center;
      gap:5px;
      color:${C.faint};
      font-size:7.5px;
      padding-bottom:5px;
    }
    .typing-bubble{
      width:55px;
      height:31px;
      display:flex;
      align-items:center;
      justify-content:center;
      gap:4px;
    }
    .typing-dot{
      width:5px;
      height:5px;
      border-radius:50%;
      background:${C.muted};
      animation:typingPulse 1.2s infinite ease-in-out;
    }
    .typing-dot:nth-child(2){animation-delay:.15s}
    .typing-dot:nth-child(3){animation-delay:.3s}
    @keyframes typingPulse{
      0%,60%,100%{opacity:.25;transform:translateY(0)}
      30%{opacity:1;transform:translateY(-3px)}
    }

    @media(max-height:760px){
      .clean-ask{padding-top:8px;padding-bottom:10px}
      .chat-top{height:46px}
      .chat-top-subtitle{display:none}
      .suggestions{margin-top:12px}
      .suggestion{min-height:38px;padding:7px 9px}
      .empty-logo{width:31px;height:31px;margin-bottom:7px}
      .empty-title{font-size:12.5px}
      .empty-copy{font-size:9.5px}
    }

    @media(max-width:800px){
      .clean-ask{padding:8px 10px 10px}
      .suggestions{grid-template-columns:1fr}
      .chat-card-full{border-radius:10px}
    }

    @media(max-width:900px){
      .dashboard-toolbar{align-items:flex-start;flex-direction:column}
      .dashboard-filters{justify-content:flex-start}
      .investigation-layout{grid-template-columns:1fr}
      .investigation-panel{min-height:420px}
      .dashboard-head,.dashboard-row{
        grid-template-columns:1.1fr 1.45fr .95fr .95fr 22px;
      }
      .dashboard-head > :nth-child(4),
      .dashboard-row > :nth-child(4),
      .dashboard-head > :nth-child(6),
      .dashboard-row > :nth-child(6){display:none}
    }

    @media(max-width:650px){
      .shipment-drawer{width:100vw}
      .detail-grid{grid-template-columns:1fr}
      .drawer-footer{align-items:stretch;flex-direction:column-reverse}
      .investigate-btn{justify-content:center}
      .drawer-nav{justify-content:space-between}
      .simple-page{padding:16px 12px}
    }

    @media(max-width:1050px){
      .sidebar{width:190px}
      .header{grid-template-columns:160px minmax(260px,1fr) auto}
      .workspace{grid-template-columns:1fr}
      .right{display:none}
      .metrics{grid-template-columns:repeat(2,1fr)}
    }
  `}</style>;
}

function Sidebar({ nav, onNav }) {
  const items = [
    ["dashboard", Icons.home, "Dashboard"],
    ["ask", Icons.chat, "Ask Wasl"],
    ["investigations", Icons.fileSearch, "Investigations"],
    ["docs", Icons.book, "Knowledge Base"],
    ["settings", Icons.gear, "Settings"],
  ];

  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="mark">W</div>
        <div>
          <div className="brand-name">wasl</div>
          <div className="brand-sub">CONTROL TOWER</div>
        </div>
      </div>

      <nav className="side-nav">
        {items.map(([key, Icon, label]) => (
          <button
            key={key}
            className={`side-button ${nav === key ? "active" : ""}`}
            onClick={() => onNav(key)}
          >
            <span className="side-icon"><Icon size={18} /></span>
            <span>{label}</span>
          </button>
        ))}
      </nav>

      <div className="profile">
        <div className="profile-avatar">ZI</div>
        <div>
          <div className="profile-name">Zahoor I.</div>
          <div className="profile-role">Operations</div>
        </div>
        <span style={{ marginLeft: "auto", color: "#c9d6e1" }}>⌄</span>
      </div>
    </aside>
  );
}

function Header({ nav, online }) {
  const title = {
    ask: "Ask Wasl",
    dashboard: "Dashboard",
    investigations: "Investigations",
    docs: "Knowledge Base",
    settings: "Settings",
  }[nav];

  return (
    <header className="header">
      <h1 className="page-title">{title}</h1>

      <div className="live">
        <span
          className="live-dot"
          style={{ background: online === false ? C.red : online ? C.green : C.faint }}
        />
        <span>{online === false ? "Offline" : online ? "Live" : "Connecting…"}</span>
      </div>
    </header>
  );
}

function AskPage({ docs, shipments, metrics, refresh }) {
  const [messages, setMessages] = useState([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const scrollRef = useRef(null);

  const suggestions = [
    "What documents are commonly required for Saudi customs clearance?",
    "What does ZATCA require for import customs documentation?",
    "When should a customs hold be escalated internally?",
    "What happens when a shipment is at risk of SLA breach?",
  ];

  useEffect(() => {
    const el = scrollRef.current;
    if (el) {
      requestAnimationFrame(() => {
        el.scrollTop = el.scrollHeight;
      });
    }
  }, [messages, busy]);

  async function send(value = text) {
    const q = value.trim();
    if (!q || busy) return;

    setMessages((m) => [
      ...m,
      {
        id: crypto.randomUUID(),
        role: "user",
        text: q,
        time: nowTime(),
      },
    ]);

    setText("");
    setBusy(true);
    setError("");

    try {
      const history = messages
        .filter(
          (message) =>
            (message.role === "user" || message.role === "assistant") &&
            String(message.text || "").trim()
        )
        .slice(-4)
        .map((message) => ({
          role: message.role,
          text: compactHistoryText(message.text),
        }));

      const r = await apiAsk(q, 5, history);

      setMessages((m) => [
        ...m,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          text: r.text || "",
          answered: Boolean(r.answered),
          citations: r.answered ? dedupeSources(r.citations || []) : [],
          time: nowTime(),
        },
      ]);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  function quit() {
    setMessages([]);
    setText("");
    setError("");
  }

  const hasChat = messages.length > 0 || busy;

  return (
    <main className="ask-page clean-ask">
      <section className="chat-card chat-card-full">
        <div className="chat-top">
          <div>
            <div className="chat-top-title">Ask Wasl</div>
            <div className="chat-top-subtitle">
              Customs, ZATCA, shipment policy, SLA and operational guidance
            </div>
          </div>

          {hasChat && (
            <button className="quit chat-quit" onClick={quit}>
              <Icons.logout size={13} />
              Quit Chat
            </button>
          )}
        </div>

        <div className="messages full-chat-messages" ref={scrollRef}>
          {!hasChat && (
            <div className="empty improved-empty">
              <div className="empty-inner suggestion-empty">
                <div className="empty-logo">W</div>
                <div className="empty-title">How can I help?</div>
                <div className="empty-copy">
                  Ask about Saudi customs, ZATCA, shipment exceptions, SLAs, or your internal knowledge base.
                </div>

                <div className="suggestions">
                  {suggestions.map((question) => (
                    <button
                      key={question}
                      className="suggestion"
                      onClick={() => send(question)}
                    >
                      <span>{question}</span>
                      <Icons.chevron size={13} />
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {messages.map((m) =>
            m.role === "user"
              ? <UserMessage key={m.id} m={m} />
              : <AssistantMessage key={m.id} m={m} />
          )}

          {busy && (
            <div className="assistant-wrap typing-wrap">
              <div className="bot">W</div>
              <div className="assistant-col">
                <div className="time">{nowTime()}</div>
                <div className="assistant-msg typing-bubble">
                  <span className="typing-dot" />
                  <span className="typing-dot" />
                  <span className="typing-dot" />
                </div>
              </div>
            </div>
          )}
        </div>

        {error && <div className="error">{error}</div>}

        <div className="composer full-composer">
          <textarea
            rows={1}
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Ask Wasl a question..."
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                send();
              }
            }}
          />
          <button className="send" onClick={() => send()} disabled={!text.trim() || busy}>
            <Icons.send size={15} />
          </button>
        </div>

        {hasChat && (
          <div className="session-footer">
            <Icons.lock size={10} />
            Session-only chat. Conversation is cleared when you quit.
          </div>
        )}
      </section>
    </main>
  );
}

function Metric({ icon, iconBg, title, value, valueColor = C.text, detail }) {
  return (
    <div className="metric">
      <div className="metric-icon" style={{ background: iconBg }}>{icon}</div>
      <div style={{ minWidth: 0 }}>
        <div className="metric-title">{title}</div>
        <div className="metric-value" style={{ color: valueColor }}>{value}</div>
        <div className="metric-detail">{detail}</div>
      </div>
    </div>
  );
}

function UserMessage({ m }) {
  return (
    <div className="user-wrap">
      <div>
        <div className="time user-time">{m.time}</div>
        <div className="user-msg">{m.text}</div>
      </div>
      <span className="ticks">✓✓</span>
    </div>
  );
}

function AssistantMessage({ m }) {
  return (
    <div className="assistant-wrap">
      <div className="bot">W</div>
      <div className="assistant-col">
        <div className="time">{m.time}</div>
        <div className="assistant-msg">
          {!m.answered && <div className="ungrounded">No grounded answer</div>}
          <FormattedAnswer text={m.text} />

          {m.answered && m.citations?.length > 0 && (
            <div className="sources">
              <div className="sources-title">Sources</div>
              <div className="chips">
                {m.citations.map((c, i) => <SourceChip key={`${c.source}-${i}`} c={c} />)}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function FormattedAnswer({ text = "" }) {
  const clean = text.replace(/\[source:[^\]]+\]/gi, "").trim();
  const lines = clean.split(/\r?\n/);
  const out = [];
  let bullets = [];

  const flush = () => {
    if (!bullets.length) return;
    out.push(
      <ul className="answer-ul" key={`u-${out.length}`}>
        {bullets.map((b, i) => <li key={i}><Inline text={b} /></li>)}
      </ul>
    );
    bullets = [];
  };

  lines.forEach((raw, i) => {
    const s = raw.trim();
    if (!s) { flush(); return; }
    if (/^[-*]\s+/.test(s)) {
      bullets.push(s.replace(/^[-*]\s+/, ""));
      return;
    }
    flush();

    if (/^###\s+/.test(s)) out.push(<h4 className="answer-h4" key={i}><Inline text={s.replace(/^###\s+/, "")} /></h4>);
    else if (/^##\s+/.test(s)) out.push(<h3 className="answer-h3" key={i}><Inline text={s.replace(/^##\s+/, "")} /></h3>);
    else if (/^#\s+/.test(s)) out.push(<h2 className="answer-h2" key={i}><Inline text={s.replace(/^#\s+/, "")} /></h2>);
    else out.push(<p className="answer-p" key={i}><Inline text={s} /></p>);
  });

  flush();
  return <>{out}</>;
}

function Inline({ text }) {
  return String(text).split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
    part.startsWith("**") && part.endsWith("**")
      ? <strong key={i}>{part.slice(2, -2)}</strong>
      : <React.Fragment key={i}>{part}</React.Fragment>
  );
}

function SourceChip({ c }) {
  const t = docType(c.source);
  return (
    <div className="source-chip">
      <div className="file-badge" style={{ background: t.bg, color: t.color }}>{t.label}</div>
      <div style={{ minWidth: 0 }}>
        <div className="source-name">{c.source}</div>
        <div className="source-meta">
          Knowledge Base
          {c.page ? ` • p. ${c.page}` : ""}
        </div>
      </div>
    </div>
  );
}

function KnowledgePanel({ docs, refresh }) {
  const inputRef = useRef(null);
  const [uploading, setUploading] = useState(false);
  const [deleting, setDeleting] = useState("");
  const [error, setError] = useState("");
  const list = docs.document_details?.length
    ? docs.document_details
    : (docs.documents || []).map((name) => ({ name, chunks: 0 }));

  async function upload(files) {
    if (!files.length) return;
    setUploading(true);
    setError("");
    try {
      for (const f of files) await uploadDocument(f);
      await refresh();
    } catch (e) {
      setError(e.message);
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  async function remove(name) {
    if (!window.confirm(`Delete "${name}" from the knowledge base?`)) return;
    setDeleting(name);
    setError("");
    try {
      await deleteDocument(name);
      await refresh();
    } catch (e) {
      setError(e.message);
    } finally {
      setDeleting("");
    }
  }

  return (
    <div className="kb">
      <div className="kb-header">
        <div className="kb-title">Knowledge Base &nbsp;ⓘ</div>
        <button className="upload" disabled={uploading} onClick={() => inputRef.current?.click()}>
          <Icons.upload size={12} />
          {uploading ? "Uploading…" : "Upload Document"}
        </button>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept=".pdf,.md,.txt"
          hidden
          onChange={(e) => upload(Array.from(e.target.files || []))}
        />
      </div>

      <div className="kb-cols">
        <span>Document</span><span>Chunks</span><span>Status</span><span />
      </div>

      <div className="kb-list">
        {list.length === 0 ? (
          <div className="kb-empty">No documents ingested yet.</div>
        ) : list.map((doc) => {
          const name = typeof doc === "string" ? doc : doc.name;
          const chunks = typeof doc === "string" ? 0 : Number(doc.chunks || 0);
          const t = docType(name);

          return (
            <div className="kb-row" key={name}>
              <div className="doc-cell">
                <div className="tiny-file" style={{ background: t.bg, color: t.color }}>{t.label}</div>
                <span className="doc-name" title={name}>{name}</span>
              </div>
              <span>{chunks.toLocaleString()}</span>
              <span><span className="status">Ingested</span></span>
              <button
                className="trash"
                disabled={deleting === name}
                onClick={() => remove(name)}
                title={`Delete ${name}`}
              >
                {deleting === name ? "…" : <Icons.trash size={12} />}
              </button>
            </div>
          );
        })}
      </div>

      {error && <div className="kb-error">{error}</div>}
      <div className="kb-footer">Showing {list.length} of {list.length} documents</div>
    </div>
  );
}

function ShipmentContext({ shipment }) {
  const fields = [
    ["Shipment", shipment.shipment_id],
    ["Status", shipment.status],
    ["Exception", shipment.exception_type],
    ["Origin", shipment.origin],
    ["Destination", shipment.destination],
    ["Carrier", shipment.carrier],
    ["SLA", shipment.sla_status],
    ["Value", `SAR ${Number(shipment.shipment_value_sar || 0).toLocaleString()}`],
  ];
  return (
    <div className="kb context">
      <div className="kb-header"><div className="kb-title">Shipment Context</div></div>
      <div className="context-body">
        {fields.map(([k, v]) => (
          <div className="context-row" key={k}>
            <span className="context-label">{k}</span>
            <span className="context-value">{v || "—"}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function ShipmentDrawer({
  shipment,
  position,
  total,
  onClose,
  onPrevious,
  onNext,
  onInvestigate,
}) {
  useEffect(() => {
    function onKeyDown(event) {
      if (event.key === "Escape") onClose();
      if (event.key === "ArrowLeft" && onPrevious) onPrevious();
      if (event.key === "ArrowRight" && onNext) onNext();
    }

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose, onPrevious, onNext]);

  if (!shipment) return null;

  const location = shipment.current_location || {};
  const highValue = Number(shipment.shipment_value_sar || 0) >= 500000;
  const hasException = shipment.exception_type && shipment.exception_type !== "none";
  const sla = shipment.sla || {};

  async function copyId() {
    try {
      await navigator.clipboard.writeText(shipment.shipment_id);
    } catch {
      // Clipboard may be unavailable on insecure local origins.
    }
  }

  return (
    <>
      <div className="drawer-backdrop" onClick={onClose} aria-hidden="true" />

      <aside
        className="shipment-drawer"
        role="dialog"
        aria-modal="true"
        aria-label={`Shipment ${shipment.shipment_id} details`}
      >
        <div className="drawer-head">
          <div className="drawer-head-top">
            <div style={{ minWidth: 0 }}>
              <div className="drawer-eyebrow">Shipment details</div>
              <div className="drawer-id-row">
                <div className="drawer-id">{shipment.shipment_id}</div>
                <button className="drawer-icon-btn" onClick={copyId} title="Copy shipment ID">
                  <Icons.copy size={13} />
                </button>
              </div>
            </div>

            <div className="drawer-head-actions">
              <button className="drawer-icon-btn" onClick={onClose} title="Close">
                <Icons.close size={15} />
              </button>
            </div>
          </div>

          <div className="drawer-summary">
            <SlaBadge status={shipment.sla_status} />
            <ExceptionBadge value={shipment.exception_type} />
            {highValue && <span className="high-value-badge">High value</span>}
          </div>
        </div>

        <div className="drawer-body">
          <div className="drawer-route">
            <div className="route-main">
              {shipment.origin || "—"} → {shipment.destination || "—"}
            </div>
            <div className="route-current">
              Current location:{" "}
              {[location.facility, location.city, location.country]
                .filter(Boolean)
                .join(", ") || "Not available"}
            </div>
          </div>

          <section className="drawer-section">
            <div className="drawer-section-title">Operational status</div>
            <div className="detail-grid">
              <DetailField label="Status" value={prettyStatus(shipment.status)} />
              <DetailField
                label="SLA position"
                value={formatSlaTime(shipment.sla_hours_remaining, shipment.sla_status)}
              />
              <DetailField label="Carrier" value={shipment.carrier} />
              <DetailField label="Shipment value" value={formatSar(shipment.shipment_value_sar)} />
              <DetailField label="Created" value={formatDateTime(shipment.created_at)} />
              <DetailField label="Last updated" value={formatDateTime(shipment.last_updated)} />
            </div>
          </section>

          {hasException && (
            <section className="drawer-section">
              <div className="drawer-section-title">Exception</div>
              <div className="detail-callout danger">
                <b>{prettyException(shipment.exception_type)}</b>
                <div style={{ marginTop: 4 }}>
                  {shipment.exception_detail || "No additional exception detail has been provided."}
                </div>
              </div>
            </section>
          )}

          <section className="drawer-section">
            <div className="drawer-section-title">SLA & commercial exposure</div>
            <div className="detail-grid">
              <DetailField label="Promised delivery" value={formatDateTime(sla.promised_delivery)} />
              <DetailField
                label="Penalty / day"
                value={formatSar(sla.penalty_per_day_sar, { emptyZero: false })}
              />
              <DetailField
                label="Potential penalty"
                value={formatSar(shipment.penalty_if_breached_sar, { emptyZero: false })}
              />
              <DetailField
                label="Maximum liability"
                value={formatSar(sla.max_liability_sar, { emptyZero: false })}
              />
            </div>
          </section>

          <section className="drawer-section">
            <div className="drawer-section-title">Customer</div>
            <div className="detail-grid">
              <DetailField label="Customer / consignee" value={shipment.customer_name} />
              <DetailField label="Contact" value={shipment.customer_contact} />
            </div>
          </section>

          <section className="drawer-section">
            <div className="drawer-section-title">Additional information</div>
            <div className="detail-grid">
              <DetailField label="Vendor CR" value={shipment.vendor_cr} mono />
              <DetailField
                label="Facility"
                value={location.facility || location.city || "—"}
              />
            </div>
          </section>

          {shipment.notes && (
            <section className="drawer-section">
              <div className="drawer-section-title">Operational notes</div>
              <div className="detail-callout neutral">{shipment.notes}</div>
            </section>
          )}
        </div>

        <div className="drawer-footer">
          <div className="drawer-nav">
            <button
              className="drawer-icon-btn"
              onClick={onPrevious}
              disabled={!onPrevious}
              title="Previous shipment"
            >
              <Icons.left size={14} />
            </button>
            <div className="drawer-nav-label">{position} / {total}</div>
            <button
              className="drawer-icon-btn"
              onClick={onNext}
              disabled={!onNext}
              title="Next shipment"
            >
              <Icons.right size={14} />
            </button>
          </div>

          {hasException && (
            <button className="investigate-btn" onClick={() => onInvestigate(shipment)}>
              <Icons.fileSearch size={14} />
              Open investigation
            </button>
          )}
        </div>
      </aside>
    </>
  );
}

function Dashboard({ shipments, metrics, onOpenInvestigation }) {
  const [filter, setFilter] = useState("all");
  const [selectedId, setSelectedId] = useState("");

  const ordered = useMemo(
    () =>
      [...shipments].sort((a, b) => {
        const priority = priorityRank(a) - priorityRank(b);
        if (priority !== 0) return priority;

        const aTime = new Date(a.last_updated || 0).getTime() || 0;
        const bTime = new Date(b.last_updated || 0).getTime() || 0;
        return bTime - aTime;
      }),
    [shipments]
  );

  const visible = useMemo(() => {
    if (filter === "attention") {
      return ordered.filter(
        (s) =>
          s.sla_status === "breached" ||
          s.sla_status === "at_risk" ||
          (s.exception_type && s.exception_type !== "none")
      );
    }
    if (filter === "breached") return ordered.filter((s) => s.sla_status === "breached");
    if (filter === "at_risk") return ordered.filter((s) => s.sla_status === "at_risk");
    return ordered;
  }, [ordered, filter]);

  const selectedIndex = visible.findIndex((s) => s.shipment_id === selectedId);
  const selectedShipment = selectedIndex >= 0 ? visible[selectedIndex] : null;

  useEffect(() => {
    if (selectedId && !selectedShipment) setSelectedId("");
  }, [selectedId, selectedShipment]);

  function openShipment(shipment) {
    setSelectedId(shipment.shipment_id);
  }

  function investigate(shipment) {
    setSelectedId("");
    onOpenInvestigation?.(shipment.shipment_id);
  }

  const filters = [
    ["all", "All", shipments.length],
    ["attention", "Needs attention", shipments.filter(
      (s) =>
        s.sla_status === "breached" ||
        s.sla_status === "at_risk" ||
        (s.exception_type && s.exception_type !== "none")
    ).length],
    ["breached", "Breached", shipments.filter((s) => s.sla_status === "breached").length],
    ["at_risk", "At risk", shipments.filter((s) => s.sla_status === "at_risk").length],
  ];

  return (
    <main className="simple-page">
      <div className="metrics" style={{ marginTop: 0 }}>
        <Metric
          icon={<Icons.box size={19}/>}
          iconBg={C.amberSoft}
          title="Active Shipments"
          value={metrics.active}
          detail={`${metrics.high} high value`}
        />
        <Metric
          icon={<Icons.alert size={19}/>}
          iconBg="#fff0e6"
          title="Open Exceptions"
          value={metrics.exceptions}
          detail={`${metrics.breached} breached`}
        />
        <Metric
          icon={<Icons.calendar size={19}/>}
          iconBg={C.blueSoft}
          title="At Risk"
          value={metrics.atRisk}
          detail="SLA attention required"
        />
        <Metric
          icon={<Icons.check size={19}/>}
          iconBg={C.greenSoft}
          title="Backend"
          value="Live"
          valueColor={C.green}
          detail="AWS production environment"
        />
      </div>

      <div className="table-card" style={{ marginTop: 14 }}>
        <div className="dashboard-toolbar">
          <div className="dashboard-toolbar-copy">
            <div className="dashboard-toolbar-title">Shipment overview</div>
            <div className="dashboard-toolbar-sub">
              Critical shipments are surfaced first. Click a row to inspect the full shipment.
            </div>
          </div>

          <div className="dashboard-filters" aria-label="Shipment filters">
            {filters.map(([key, label, count]) => (
              <button
                key={key}
                className={`filter-chip ${filter === key ? "active" : ""}`}
                onClick={() => setFilter(key)}
              >
                {label} · {count}
              </button>
            ))}
          </div>
        </div>

        <div className="dashboard-head">
          <span>Shipment</span>
          <span>Route</span>
          <span>Status</span>
          <span>Exception</span>
          <span>SLA</span>
          <span style={{ textAlign: "right" }}>Value</span>
          <span />
        </div>

        {visible.length === 0 ? (
          <div className="dashboard-empty">No shipments match this filter.</div>
        ) : (
          visible.map((s) => (
            <button
              type="button"
              className={`dashboard-row ${selectedId === s.shipment_id ? "selected" : ""}`}
              key={s.shipment_id}
              onClick={() => openShipment(s)}
              aria-label={`Open shipment ${s.shipment_id}`}
            >
              <b style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: 8.5 }}>
                {s.shipment_id}
              </b>

              <span style={{ color: C.text2 }}>
                {s.origin} → {s.destination}
              </span>

              <span>{prettyStatus(s.status)}</span>

              <ExceptionBadge value={s.exception_type} />

              <SlaBadge status={s.sla_status} />

              <span style={{ textAlign: "right", fontWeight: 600 }}>
                {formatSar(s.shipment_value_sar)}
              </span>

              <span className="row-chevron">
                <Icons.chevron size={13} />
              </span>
            </button>
          ))
        )}
      </div>

      {selectedShipment && (
        <ShipmentDrawer
          shipment={selectedShipment}
          position={selectedIndex + 1}
          total={visible.length}
          onClose={() => setSelectedId("")}
          onPrevious={
            selectedIndex > 0
              ? () => setSelectedId(visible[selectedIndex - 1].shipment_id)
              : null
          }
          onNext={
            selectedIndex < visible.length - 1
              ? () => setSelectedId(visible[selectedIndex + 1].shipment_id)
              : null
          }
          onInvestigate={investigate}
        />
      )}
    </main>
  );
}

function Investigations({
  shipments,
  initialShipmentId = "",
  onInitialHandled,
}) {
  const rows = useMemo(
    () =>
      shipments
        .filter((s) => s.exception_type && s.exception_type !== "none")
        .sort((a, b) => {
          const priority = priorityRank(a) - priorityRank(b);
          if (priority !== 0) return priority;
          return (new Date(b.last_updated || 0).getTime() || 0)
            - (new Date(a.last_updated || 0).getTime() || 0);
        }),
    [shipments]
  );

  const [selectedId, setSelectedId] = useState("");
  const [result, setResult] = useState(null);
  const [phase, setPhase] = useState("idle");
  const [error, setError] = useState("");
  const [decision, setDecision] = useState("");

  const selectedShipment = useMemo(
    () => rows.find((s) => s.shipment_id === selectedId) || null,
    [rows, selectedId]
  );

  async function runInvestigation(shipment) {
    if (!shipment || phase === "running" || phase === "deciding") return;

    setSelectedId(shipment.shipment_id);
    setResult(null);
    setError("");
    setDecision("");
    setPhase("running");

    try {
      const response = await startInvestigation(shipment.shipment_id);
      setResult(response);
      setPhase(response?.drafted_action ? "paused" : "done");
    } catch (e) {
      setError(e.message || "Investigation failed.");
      setPhase("error");
    }
  }

  useEffect(() => {
    if (!initialShipmentId || rows.length === 0) return;

    const shipment = rows.find((s) => s.shipment_id === initialShipmentId);
    if (shipment) {
      runInvestigation(shipment);
    }

    onInitialHandled?.();
    // initialShipmentId is intentionally a one-shot navigation target.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialShipmentId, rows.length]);

  function selectForReview(shipment) {
    setSelectedId(shipment.shipment_id);
    setResult(null);
    setError("");
    setDecision("");
    setPhase("idle");
  }

  async function decide(approved) {
    if (!result?.investigation_id || phase === "deciding") return;

    setPhase("deciding");
    setError("");

    try {
      const response = await decideInvestigation(
        result.investigation_id,
        approved
      );

      setResult(response);
      setDecision(approved ? "approved" : "rejected");
      setPhase("done");
    } catch (e) {
      setError(e.message || "Could not submit the decision.");
      setPhase("error");
    }
  }

  const urgency = String(result?.assessment?.urgency || "").toLowerCase();
  const urgencyClass =
    urgency === "critical"
      ? "urgency-critical"
      : ["high", "warning", "urgent"].includes(urgency)
      ? "urgency-warning"
      : "urgency-normal";

  return (
    <main className="simple-page">
      <div className={`investigation-layout ${selectedShipment ? "with-panel" : ""}`}>
        <section className="investigation-queue">
          <div className="investigation-queue-head">
            <div>
              <div className="investigation-queue-title">Open investigations</div>
              <div className="investigation-queue-sub">
                Select a shipment to review, then run the agent investigation.
              </div>
            </div>
            <span className="investigation-count">{rows.length}</span>
          </div>

          <div className="investigation-head">
            <span>Shipment</span>
            <span>Exception</span>
            <span>SLA</span>
            <span />
          </div>

          {rows.length === 0 ? (
            <div className="dashboard-empty">No open shipment exceptions.</div>
          ) : (
            rows.map((s) => (
              <button
                type="button"
                className={`investigation-row ${
                  selectedId === s.shipment_id ? "selected" : ""
                }`}
                key={s.shipment_id}
                onClick={() => selectForReview(s)}
              >
                <span style={{ minWidth: 0 }}>
                  <b
                    style={{
                      fontFamily: "'IBM Plex Mono',monospace",
                      fontSize: 8,
                    }}
                  >
                    {s.shipment_id}
                  </b>
                  <span className="investigation-route">
                    {s.origin} → {s.destination}
                  </span>
                </span>

                <ExceptionBadge value={s.exception_type} />

                <SlaBadge status={s.sla_status} />

                <span className="investigation-chevron">
                  <Icons.chevron size={12} />
                </span>
              </button>
            ))
          )}
        </section>

        {selectedShipment && (
          <section className="investigation-panel">
            <>
              <div className="investigation-panel-head">
                <div style={{ minWidth: 0 }}>
                  <div className="investigation-panel-id">
                    {selectedShipment.shipment_id}
                  </div>
                  <div className="investigation-panel-route">
                    {selectedShipment.origin} → {selectedShipment.destination}
                    {" · "}
                    {selectedShipment.carrier || "Carrier unavailable"}
                  </div>
                </div>

                <div style={{ display: "flex", gap: 6, flexWrap: "wrap", justifyContent: "flex-end" }}>
                  <SlaBadge status={selectedShipment.sla_status} />
                  <ExceptionBadge value={selectedShipment.exception_type} />
                </div>
              </div>

              <div className="investigation-panel-body">
                {phase === "idle" && (
                  <>
                    <div className="agent-section">
                      <div className="agent-section-title">Investigation context</div>
                      <div className="detail-grid">
                        <DetailField
                          label="Current status"
                          value={prettyStatus(selectedShipment.status)}
                        />
                        <DetailField
                          label="SLA position"
                          value={formatSlaTime(
                            selectedShipment.sla_hours_remaining,
                            selectedShipment.sla_status
                          )}
                        />
                        <DetailField
                          label="Current location"
                          value={[
                            selectedShipment.current_location?.facility,
                            selectedShipment.current_location?.city,
                          ]
                            .filter(Boolean)
                            .join(", ")}
                        />
                        <DetailField
                          label="Shipment value"
                          value={formatSar(selectedShipment.shipment_value_sar)}
                        />
                      </div>
                    </div>

                    <div className="agent-section">
                      <div className="agent-section-title">Exception to investigate</div>
                      <div className="detail-callout danger">
                        <b>{prettyException(selectedShipment.exception_type)}</b>
                        <div style={{ marginTop: 4 }}>
                          {selectedShipment.exception_detail ||
                            "No additional exception detail is available."}
                        </div>
                      </div>
                    </div>

                    <button
                      className="investigation-run"
                      onClick={() => runInvestigation(selectedShipment)}
                    >
                      <Icons.fileSearch size={14} />
                      Run agent investigation
                    </button>
                  </>
                )}

                {phase === "running" && (
                  <div className="agent-loading">
                    <div>
                      <div className="agent-spinner" />
                      <div style={{ fontSize: 10, fontWeight: 700, color: C.text }}>
                        Wasl is investigating…
                      </div>
                      <div className="agent-steps">
                        Shipment lookup · exception assessment · policy retrieval ·
                        SLA calculation · action drafting
                      </div>
                    </div>
                  </div>
                )}

                {error && (
                  <div className="agent-error">
                    {error}
                    <div style={{ marginTop: 8 }}>
                      <button
                        className="filter-chip"
                        onClick={() => runInvestigation(selectedShipment)}
                      >
                        Try again
                      </button>
                    </div>
                  </div>
                )}

                {result && phase !== "running" && (
                  <>
                    {Array.isArray(result.trace) && result.trace.length > 0 && (
                      <div className="agent-section">
                        <div className="agent-section-title">Agent trace</div>
                        <div className="agent-trace">
                          {result.trace.map((step, index) => (
                            <div className="agent-trace-row" key={`${step.node}-${index}`}>
                              <span className="agent-trace-dot" />
                              <span className="agent-trace-node">{step.node}</span>
                              <span className="agent-trace-detail">{step.detail}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {result.assessment && (
                      <div className="agent-section">
                        <div className="agent-section-title">Assessment</div>
                        <div className="assessment-card">
                          <div className="assessment-top">
                            <b style={{ fontSize: 9.5 }}>Agent assessment</b>
                            {urgency && (
                              <span className={`urgency-badge ${urgencyClass}`}>
                                {urgency}
                              </span>
                            )}
                          </div>

                          <div className="assessment-text">
                            {result.assessment.summary || "No assessment summary returned."}
                          </div>

                          {result.sla_status && (
                            <div
                              className={`sla-alert ${
                                result.sla_status.already_breached
                                  ? "danger"
                                  : "warning"
                              }`}
                            >
                              {result.sla_status.already_breached
                                ? `SLA breached · potential penalty ${formatSar(
                                    result.sla_status.penalty_if_breached_sar,
                                    { emptyZero: false }
                                  )}`
                                : `${Math.max(
                                    0,
                                    Math.round(
                                      Number(
                                        result.sla_status.hours_until_breach || 0
                                      )
                                    )
                                  )}h until SLA breach`}
                            </div>
                          )}
                        </div>
                      </div>
                    )}

                    {!result.drafted_action && (
                      <div className="agent-section">
                        <div className="agent-section-title">Outcome</div>
                        <div className="resolved-card">
                          <b>No drafted external action required.</b>
                          <div style={{ marginTop: 5 }}>
                            {result.summary ||
                              "The investigation completed without a drafted action."}
                          </div>
                        </div>
                      </div>
                    )}

                    {result.drafted_action && (
                      <div className="agent-section">
                        <div className="agent-section-title">Recommended action</div>

                        <div className="draft-card">
                          <div className="draft-head">
                            <span className="draft-label">Draft only</span>
                            <span className="draft-recipient">
                              → {result.drafted_action.recipient_label || "Recipient"}
                            </span>
                          </div>

                          <div className="draft-body">
                            <div className="draft-subject">
                              {result.drafted_action.subject || "Draft action"}
                            </div>
                            <div className="draft-message">
                              {result.drafted_action.body || ""}
                            </div>
                          </div>
                        </div>

                        <div className="approval-note">
                          Human approval is required. Wasl v1 does not automatically
                          send external communications; approval marks the proposed
                          action as actionable and records the decision.
                        </div>

                        {phase === "paused" && (
                          <div className="approval-actions">
                            <button
                              className="approve-btn"
                              onClick={() => decide(true)}
                            >
                              Approve action
                            </button>
                            <button
                              className="reject-btn"
                              onClick={() => decide(false)}
                            >
                              Reject
                            </button>
                          </div>
                        )}

                        {phase === "deciding" && (
                          <div
                            style={{
                              textAlign: "center",
                              fontSize: 8.5,
                              color: C.muted,
                              padding: "10px 0 2px",
                            }}
                          >
                            Recording decision…
                          </div>
                        )}

                        {phase === "done" && decision && (
                          <div
                            className={`decision-banner ${
                              decision === "approved" ? "approved" : "rejected"
                            }`}
                          >
                            <Icons.check size={13} />
                            {decision === "approved"
                              ? "Approved — action marked actionable and logged."
                              : "Rejected — no external action approved."}
                          </div>
                        )}
                      </div>
                    )}
                  </>
                )}
              </div>
            </>
          </section>
        )}
      </div>
    </main>
  );
}

function DocumentsPage({ docs, refresh }) {
  return (
    <main className="simple-page" style={{ maxWidth: 900 }}>
      <KnowledgePanel docs={docs} refresh={refresh} />
    </main>
  );
}

function Settings() {
  return (
    <main className="simple-page">
      <div className="table-card" style={{ maxWidth: 700 }}>
        <div className="table-head">Session & privacy</div>
        <div style={{ padding: 18, fontSize: 11, lineHeight: 1.65, color: C.text2 }}>
          Conversation messages remain only for the current frontend session. Clicking <b>Quit Session</b> clears them.
        </div>
      </div>
    </main>
  );
}