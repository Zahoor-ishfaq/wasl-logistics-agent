import React, { useState, useRef, useMemo, useEffect } from "react";
import {
  ask as apiAsk,
  startInvestigation,
  decideInvestigation,
  listDocuments,
  uploadDocument,
  getHealth,
  listShipments,
} from "./api.js";

// ============================================================================
// Wasl — Agentic Logistics Control Tower (live UI, wired to FastAPI)
// Design: enterprise v3 (Linear / Stripe / Datadog patterns).
// Shipment status, exceptions, routes, SLA values, and customer details are
// loaded live from PostgreSQL through GET /api/shipments.
// ============================================================================

const C = {
  bg: "#FAFAF8", surface: "#FFFFFF", sidebar: "#0C1C2E", sidebarHover: "#16293D",
  ink: "#111820", ink2: "#3D4A57", muted: "#6B7883", faint: "#98A2AD",
  line: "#ECEAE3", line2: "#F2F0EA", lineDark: "#1E3348",
  amber: "#D9971E", amberBg: "#FBF3E2",
  red: "#C0392B", redBg: "#FBECEA",
  green: "#1E7A54", greenBg: "#E7F3EC",
  blue: "#2C6DB5", blueBg: "#E9F1FA",
  purple: "#6D4B9F", purpleBg: "#F0EAF7",
  slate: "#5E6B78", slateBg: "#EEF1F3",
};

const EX_LABEL = { customs_hold: "Customs hold", cross_border: "Cross-border", supplier_delay: "Supplier delay", holiday_closure: "Holiday closure", carrier_delay: "Carrier delay", failed_delivery: "Failed delivery", none: "Clear" };
const EX_STATE = { customs_hold: "red", cross_border: "purple", supplier_delay: "amber", holiday_closure: "slate", carrier_delay: "amber", failed_delivery: "red", none: "green" };
const STATUS_LABEL = { held: "Held", at_customs: "At customs", pending: "Pending", in_transit: "In transit", out_for_delivery: "Out for delivery", delivered: "Delivered", failed_delivery: "Failed delivery", returned: "Returned" };

const money = (n) => "SAR " + n.toLocaleString();
const stateColor = (k) => ({ red: C.red, green: C.green, amber: C.amber, purple: C.purple, slate: C.slate, blue: C.blue }[k]);
const stateBg = (k) => ({ red: C.redBg, green: C.greenBg, amber: C.amberBg, purple: C.purpleBg, slate: C.slateBg, blue: C.blueBg }[k]);

export default function App() {
  const [nav, setNav] = useState("tower");
  const [collapsed, setCollapsed] = useState(false);
  const [online, setOnline] = useState(null);
  const w = collapsed ? 68 : 248;

  useEffect(() => {
    getHealth().then(() => setOnline(true)).catch(() => setOnline(false));
  }, []);

  return (
    <div style={{ minHeight: "100vh", background: C.bg, color: C.ink, fontFamily: "'Inter',system-ui,sans-serif", display: "flex" }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;450;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap');
        *{box-sizing:border-box;} body{margin:0;}
        .mono{font-family:'IBM Plex Mono',monospace;font-feature-settings:'tnum';}
        .navitem{transition:background .12s,color .12s;cursor:pointer;}
        .navitem:hover{background:${C.sidebarHover};}
        .btn{transition:transform .08s,opacity .15s,background .15s;cursor:pointer;}
        .btn:active{transform:translateY(1px);} .btn:disabled{opacity:.45;cursor:not-allowed;}
        .trow{transition:background .1s;cursor:pointer;} .trow:hover{background:${C.line2};}
        .kpi{transition:box-shadow .15s;} .kpi:hover{box-shadow:0 1px 3px rgba(16,24,32,.06),0 8px 24px rgba(16,24,32,.05);}
        .chip{transition:all .12s;cursor:pointer;}
        input,select{font-family:inherit;outline:none;}
        input:focus,select:focus{border-color:${C.amber}!important;box-shadow:0 0 0 3px ${C.amberBg};}
        @keyframes fade{from{opacity:0;transform:translateY(5px);}to{opacity:1;transform:none;}}
        .fade{animation:fade .3s ease both;}
        @keyframes spin{to{transform:rotate(360deg);}}
        .spin{animation:spin .7s linear infinite;}
        ::-webkit-scrollbar{width:9px;height:9px;} ::-webkit-scrollbar-thumb{background:#D8D5CC;border-radius:5px;}
        @media (prefers-reduced-motion:reduce){.fade,.spin{animation:none;}}
      `}</style>

      <aside style={{ width: w, background: C.sidebar, minHeight: "100vh", position: "sticky", top: 0, display: "flex", flexDirection: "column", transition: "width .18s", flexShrink: 0 }}>
        <div style={{ height: 60, display: "flex", alignItems: "center", gap: 11, padding: collapsed ? "0 18px" : "0 20px", borderBottom: `1px solid ${C.lineDark}` }}>
          <Logo />
          {!collapsed && <div><div style={{ color: "#fff", fontWeight: 700, fontSize: 15.5 }}>Wasl</div><div style={{ color: C.faint, fontSize: 9.5, letterSpacing: 1.8, textTransform: "uppercase" }}>Control Tower</div></div>}
        </div>
        <nav style={{ padding: "12px 10px", flex: 1 }}>
          {!collapsed && <div style={{ fontSize: 10, letterSpacing: 1.4, textTransform: "uppercase", color: C.faint, padding: "8px 12px 6px" }}>Operations</div>}
          <NavItem icon="◧" label="Control Tower" active={nav === "tower"} collapsed={collapsed} onClick={() => setNav("tower")} />
          <NavItem icon="◎" label="Ask" active={nav === "ask"} collapsed={collapsed} onClick={() => setNav("ask")} />
          {!collapsed && <div style={{ fontSize: 10, letterSpacing: 1.4, textTransform: "uppercase", color: C.faint, padding: "16px 12px 6px" }}>Knowledge</div>}
          <NavItem icon="◆" label="Knowledge Base" active={nav === "docs"} collapsed={collapsed} onClick={() => setNav("docs")} />
        </nav>
        <div style={{ padding: 10, borderTop: `1px solid ${C.lineDark}` }}>
          <div className="navitem" onClick={() => setCollapsed(c => !c)} style={{ display: "flex", alignItems: "center", gap: 11, padding: "9px 12px", borderRadius: 7, color: C.faint, fontSize: 13 }}>
            <span>{collapsed ? "»" : "«"}</span>{!collapsed && <span>Collapse</span>}
          </div>
          {!collapsed && (
            <div style={{ display: "flex", alignItems: "center", gap: 9, padding: "10px 12px" }}>
              <div style={{ width: 28, height: 28, borderRadius: "50%", background: C.amber, display: "grid", placeItems: "center", color: C.sidebar, fontWeight: 700, fontSize: 12 }}>ZI</div>
              <div><div style={{ color: "#E8EDF1", fontSize: 12.5, fontWeight: 500 }}>Zahoor I.</div><div style={{ color: C.faint, fontSize: 10.5 }}>Ops · Jeddah</div></div>
            </div>
          )}
        </div>
      </aside>

      <div style={{ flex: 1, minWidth: 0 }}>
        <header style={{ height: 60, background: C.surface, borderBottom: `1px solid ${C.line}`, display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0 28px", position: "sticky", top: 0, zIndex: 5 }}>
          <h1 style={{ margin: 0, fontSize: 16, fontWeight: 600 }}>{nav === "tower" ? "Control Tower" : nav === "ask" ? "Ask the Knowledge Base" : "Knowledge Base"}</h1>
          <div style={{ display: "flex", alignItems: "center", gap: 7 }}>
            <span style={{ width: 7, height: 7, borderRadius: "50%", background: online === false ? C.red : online ? C.green : C.faint }} />
            <span style={{ fontSize: 12.5, color: C.muted }}>{online === false ? "Backend offline" : online ? "Live" : "Connecting…"}</span>
          </div>
        </header>
        <main style={{ padding: "24px 28px 72px", maxWidth: 1320, margin: "0 auto" }}>
          {online === false && <OfflineNote />}
          {nav === "tower" && <Tower />}
          {nav === "ask" && <Ask />}
          {nav === "docs" && <Docs />}
        </main>
      </div>
    </div>
  );
}

function OfflineNote() {
  return (
    <div style={{ background: C.redBg, border: `1px solid ${C.red}22`, borderRadius: 9, padding: "13px 16px", marginBottom: 18, fontSize: 13, color: C.red }}>
      Can't reach the backend. Start it with <span className="mono" style={{ fontWeight: 600 }}>uvicorn app.main:app --reload</span> and check your VITE_API_KEY matches the backend API_KEY.
    </div>
  );
}

// ---------------------------------------------------------------------------
// CONTROL TOWER
// ---------------------------------------------------------------------------
function Tower() {
  const [sel, setSel] = useState(null);
  const [inv, setInv] = useState(null);      // live investigation result
  const [phase, setPhase] = useState("idle"); // idle|running|paused|deciding|done|error
  const [err, setErr] = useState("");
  const [decision, setDecision] = useState(null);
  const [statusF, setStatusF] = useState("all");
  const [exF, setExF] = useState("all");
  const [sort, setSort] = useState("sla");
  const [roster, setRoster] = useState([]);

  useEffect(() => {
    listShipments()
      .then((data) => {
        setRoster(
          data.map((s) => ({
            id: s.shipment_id,
            status: s.status,
            exception: s.exception_type,
            route: `${s.origin} → ${s.destination}`,
            customer: s.customer_name,
            sla: s.sla_status,
            slaHours: s.sla_hours_remaining,
            slaBreached: Boolean(s.sla_breached),
            value: Number(s.shipment_value_sar ?? 0),
          }))
        );
      })
      .catch((e) => setErr(e.message));
  }, []);

  const kpis = useMemo(() => {
    const active = roster.filter((s) => s.status !== "delivered");
    const delivered = roster.filter((s) => s.status === "delivered");
    const deliveredOnTime = delivered.filter((s) => !s.slaBreached).length;
    const onTime = delivered.length
      ? Math.round((deliveredOnTime / delivered.length) * 100)
      : 0;

    return {
      open: active.filter((s) => s.exception !== "none").length,
      breached: active.filter((s) => s.sla === "breached").length,
      atRisk: active.filter((s) => s.sla === "at_risk").length,
      delivered: delivered.length,
      deliveredOnTime,
      onTime,
    };
  }, [roster]);

  const rows = useMemo(() => {
    let list = roster.filter(s => (statusF === "all" || s.status === statusF) && (exF === "all" || s.exception === exF));
    const rank = { breached: 0, at_risk: 1, ok: 2 };
    if (sort === "sla") list = [...list].sort((a, b) => (rank[a.sla] - rank[b.sla]) || ((a.slaHours ?? 999) - (b.slaHours ?? 999)));
    if (sort === "value") list = [...list].sort((a, b) => b.value - a.value);
    return list;
  }, [roster, statusF, exF, sort]);

  async function start(s) {
    setSel(s); setInv(null); setDecision(null); setErr(""); setPhase("running");
    try {
      const result = await startInvestigation(s.id);
      setInv(result);
      setPhase(result.drafted_action ? "paused" : "done");
    } catch (e) {
      setErr(e.message); setPhase("error");
    }
  }

  async function decide(approved) {
    if (!inv?.investigation_id) return;
    setPhase("deciding");
    try {
      const result = await decideInvestigation(inv.investigation_id, approved);
      setInv(result); setDecision(approved ? "approved" : "rejected"); setPhase("done");
    } catch (e) {
      setErr(e.message); setPhase("error");
    }
  }

  // Dismiss the investigation panel and return to the queue.
  function close() {
    setSel(null); setInv(null); setDecision(null); setErr(""); setPhase("idle");
  }

  return (
    <div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 14, marginBottom: 22 }}>
        <Kpi label="Open exceptions" value={kpis.open} delta="requiring review" spark={[3,4,4,5,6,6,7]} />
        <Kpi label="SLA breached" value={kpis.breached} delta="penalty accruing" deltaState="red" state="red" spark={[1,1,2,2,3,3,3]} />
        <Kpi label="SLA at risk" value={kpis.atRisk} delta="< 12h to breach" deltaState="amber" state="amber" spark={[2,3,2,3,3,3,3]} />
        <Kpi
          label="On-time delivered"
          value={`${kpis.onTime}%`}
          delta={`${kpis.deliveredOnTime}/${kpis.delivered} delivered on time`}
          deltaState="green"
          state="green"
        />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: sel ? "1.1fr 1fr" : "1fr", gap: 20, alignItems: "start" }}>
        <Panel>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "14px 16px", borderBottom: `1px solid ${C.line}` }}>
            <div style={{ display: "flex", alignItems: "center", gap: 9 }}>
              <span style={{ fontSize: 13.5, fontWeight: 600 }}>Exception queue</span>
              <span style={{ fontSize: 11.5, color: C.muted, background: C.slateBg, padding: "2px 8px", borderRadius: 20 }}>{rows.length}</span>
            </div>
            <div style={{ display: "flex", gap: 7 }}>
              <MiniSelect value={statusF} onChange={setStatusF} options={[["all", "Status"], ["held", "Held"], ["at_customs", "At customs"], ["pending", "Pending"], ["in_transit", "In transit"]]} />
              <MiniSelect value={exF} onChange={setExF} options={[["all", "Type"], ["customs_hold", "Customs"], ["cross_border", "Cross-border"], ["supplier_delay", "Supplier"], ["holiday_closure", "Holiday"]]} />
              <MiniSelect value={sort} onChange={setSort} options={[["sla", "Sort: SLA"], ["value", "Sort: Value"]]} />
            </div>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1.4fr 1.3fr .9fr .8fr", padding: "9px 16px", borderBottom: `1px solid ${C.line}`, fontSize: 10.5, letterSpacing: .8, textTransform: "uppercase", color: C.faint, fontWeight: 600 }}>
            <div>Shipment</div><div>Exception</div><div>SLA</div><div style={{ textAlign: "right" }}>Value</div>
          </div>
          <div style={{ maxHeight: 560, overflowY: "auto" }}>
            {rows.map(s => (
              <div key={s.id} className="trow" onClick={() => start(s)}
                style={{ display: "grid", gridTemplateColumns: "1.4fr 1.3fr .9fr .8fr", padding: "12px 16px", borderBottom: `1px solid ${C.line2}`, alignItems: "center", background: sel?.id === s.id ? C.amberBg : "transparent", borderLeft: `2px solid ${sel?.id === s.id ? C.amber : "transparent"}` }}>
                <div><div className="mono" style={{ fontSize: 12.5, fontWeight: 600 }}>{s.id}</div><div style={{ fontSize: 11.5, color: C.muted, marginTop: 2 }}>{s.route}</div></div>
                <div><StateTag state={EX_STATE[s.exception]} label={EX_LABEL[s.exception]} /><div style={{ fontSize: 11, color: C.faint, marginTop: 3 }}>{STATUS_LABEL[s.status]}</div></div>
                <div><SlaTag sla={s.sla} hours={s.slaHours} /></div>
                <div className="mono" style={{ fontSize: 12, textAlign: "right", color: C.ink2 }}>{(s.value / 1000).toFixed(0)}k</div>
              </div>
            ))}
          </div>
        </Panel>

        {sel && (
          <div className="fade">
            <Panel>
              <div style={{ padding: "16px 18px", borderBottom: `1px solid ${C.line}`, display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12 }}>
                <div>
                  <div className="mono" style={{ fontSize: 15, fontWeight: 600 }}>{sel.id}</div>
                  <div style={{ fontSize: 12, color: C.muted, marginTop: 3 }}>{sel.route} · {sel.customer}</div>
                  <div style={{ fontSize: 12, color: C.muted, marginTop: 1 }}>{money(sel.value)}</div>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <StateTag state={EX_STATE[sel.exception]} label={EX_LABEL[sel.exception]} big />
                  <button
                    onClick={close}
                    title="Close"
                    aria-label="Close investigation"
                    className="btn"
                    style={{ background: "transparent", border: "none", color: C.muted, fontSize: 20, lineHeight: 1, cursor: "pointer", padding: "2px 6px", borderRadius: 6 }}
                  >×</button>
                </div>
              </div>

              {(phase === "running") && (
                <div style={{ padding: "36px 18px", textAlign: "center", color: C.muted }}>
                  <Spinner /><div style={{ fontSize: 13, marginTop: 12 }}>Agent investigating…</div>
                  <div style={{ fontSize: 11.5, color: C.faint, marginTop: 4 }}>Looking up shipment · assessing · retrieving policy · drafting</div>
                </div>
              )}

              {phase === "error" && (
                <div style={{ margin: 16, padding: 14, background: C.redBg, border: `1px solid ${C.red}22`, borderRadius: 7, fontSize: 13, color: C.red }}>{err}</div>
              )}

              {inv && phase !== "running" && (
                <>
                  {inv.trace?.length > 0 && (
                    <div style={{ padding: "14px 18px", background: C.sidebar }}>
                      <div style={{ fontSize: 10, letterSpacing: 1.4, textTransform: "uppercase", color: C.faint, marginBottom: 11 }}>Agent investigation</div>
                      {inv.trace.map((t, i) => (
                        <div key={i} style={{ display: "flex", alignItems: "center", gap: 10, padding: "5px 0" }}>
                          <span style={{ width: 6, height: 6, borderRadius: "50%", background: C.amber, flexShrink: 0 }} />
                          <span className="mono" style={{ fontSize: 11, color: "#9FB0BF", minWidth: 150 }}>{t.node}</span>
                          <span style={{ fontSize: 12, color: "#DCE4EB" }}>{t.detail}</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {!inv.drafted_action && (
                    <div style={{ padding: 18 }}>
                      <div style={{ borderLeft: `3px solid ${C.slate}`, background: C.slateBg, borderRadius: 6, padding: 16 }}>
                        <div style={{ fontSize: 10, letterSpacing: 1.3, textTransform: "uppercase", color: C.slate, marginBottom: 8, fontWeight: 600 }}>Resolved — no action required</div>
                        <p style={{ margin: 0, fontSize: 13, lineHeight: 1.6, color: C.ink2 }}>{inv.summary}</p>
                      </div>
                      <button className="btn" onClick={close} style={{ width: "100%", marginTop: 12, background: C.sidebar, color: "#fff", border: "none", borderRadius: 7, padding: 11, fontSize: 13, fontWeight: 600 }}>Back to queue</button>
                    </div>
                  )}

                  {inv.drafted_action && (
                    <div style={{ padding: 18 }}>
                      {inv.assessment && (
                        <>
                          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 9 }}>
                            <span style={{ fontSize: 10, letterSpacing: 1.3, textTransform: "uppercase", color: C.faint, fontWeight: 600 }}>Assessment</span>
                            <StateTag state={inv.assessment.urgency === "critical" ? "red" : "amber"} label={inv.assessment.urgency} />
                          </div>
                          <p style={{ margin: "0 0 10px", fontSize: 13, lineHeight: 1.6, color: C.ink2 }}>{inv.assessment.summary}</p>
                        </>
                      )}
                      {inv.sla_status && (
                        <div style={{ fontSize: 11.5, color: C.red, fontWeight: 600, marginBottom: 16 }}>
                          {inv.sla_status.already_breached ? `SLA breached · penalty ~${inv.sla_status.penalty_if_breached_sar} SAR` : `${inv.sla_status.hours_until_breach}h until breach`}
                        </div>
                      )}

                      <div style={{ border: `1px solid ${C.line}`, borderRadius: 8, overflow: "hidden", marginBottom: 14 }}>
                        <div style={{ background: C.line2, padding: "9px 14px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                          <span style={{ fontSize: 10, letterSpacing: 1.3, textTransform: "uppercase", color: C.muted, fontWeight: 600 }}>Recommended action</span>
                          <span style={{ fontSize: 11.5, fontWeight: 600, color: C.ink2 }}>→ {inv.drafted_action.recipient_label}</span>
                        </div>
                        <div style={{ padding: 14 }}>
                          <div className="mono" style={{ fontSize: 12, fontWeight: 600, marginBottom: 9 }}>{inv.drafted_action.subject}</div>
                          <p style={{ margin: 0, fontSize: 12.5, lineHeight: 1.65, whiteSpace: "pre-wrap", color: C.ink2 }}>{inv.drafted_action.body}</p>
                        </div>
                      </div>

                      {phase === "paused" && (
                        <div style={{ display: "flex", gap: 10 }}>
                          <button className="btn" onClick={() => decide(true)} style={{ flex: 1, background: C.green, color: "#fff", border: "none", borderRadius: 7, padding: 11, fontSize: 13, fontWeight: 600 }}>Approve &amp; send</button>
                          <button className="btn" onClick={() => decide(false)} style={{ flex: 1, background: C.surface, color: C.red, border: `1px solid ${C.line}`, borderRadius: 7, padding: 11, fontSize: 13, fontWeight: 600 }}>Reject</button>
                        </div>
                      )}
                      {phase === "deciding" && <div style={{ fontSize: 12.5, color: C.muted, textAlign: "center", padding: 8 }}>Submitting decision…</div>}
                      {phase === "done" && decision && (
                        <>
                          <div style={{ background: decision === "approved" ? C.greenBg : C.redBg, border: `1px solid ${decision === "approved" ? C.green : C.red}22`, borderRadius: 7, padding: 13, display: "flex", alignItems: "center", gap: 9 }}>
                            <span style={{ fontSize: 15, color: decision === "approved" ? C.green : C.red }}>{decision === "approved" ? "✓" : "✕"}</span>
                            <span style={{ fontSize: 12.5, fontWeight: 600, color: decision === "approved" ? C.green : C.red }}>{decision === "approved" ? "Approved — action sent and logged." : "Rejected — nothing sent."}</span>
                          </div>
                          <button className="btn" onClick={close} style={{ width: "100%", marginTop: 10, background: C.sidebar, color: "#fff", border: "none", borderRadius: 7, padding: 11, fontSize: 13, fontWeight: 600 }}>Back to queue</button>
                        </>
                      )}
                    </div>
                  )}
                </>
              )}
            </Panel>
          </div>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// ASK
// ---------------------------------------------------------------------------
function Ask() {
  const [q, setQ] = useState(""); const [ans, setAns] = useState(null); const [loading, setLoading] = useState(false); const [err, setErr] = useState("");
  async function run() {
    if (!q.trim()) return;
    setLoading(true); setAns(null); setErr("");
    try { setAns(await apiAsk(q, 5)); } catch (e) { setErr(e.message); } finally { setLoading(false); }
  }
  return (
    <div style={{ maxWidth: 760 }}>
      <div style={{ display: "flex", gap: 9, marginBottom: 10 }}>
        <input value={q} onChange={e => setQ(e.target.value)} onKeyDown={e => e.key === "Enter" && run()} placeholder="Ask about customs, SLAs, delivery policy…"
          style={{ flex: 1, border: `1px solid ${C.line}`, borderRadius: 8, padding: "12px 14px", fontSize: 14, background: C.surface }} />
        <button className="btn" onClick={run} disabled={loading} style={{ background: C.ink, color: "#fff", border: "none", borderRadius: 8, padding: "0 22px", fontSize: 13.5, fontWeight: 600 }}>{loading ? "…" : "Ask"}</button>
      </div>
      <div style={{ display: "flex", gap: 7, flexWrap: "wrap", marginBottom: 22 }}>
        {["What documents are required to import goods?", "Does an Eid delay count as an SLA breach?", "What is the re-delivery policy?"].map(s => (
          <button key={s} onClick={() => setQ(s)} className="chip" style={{ background: C.surface, border: `1px solid ${C.line}`, borderRadius: 20, padding: "6px 12px", fontSize: 12, color: C.muted }}>{s}</button>
        ))}
      </div>
      {loading && <div style={{ fontSize: 13, color: C.muted, display: "flex", alignItems: "center", gap: 9 }}><Spinner small /> Retrieving and grounding…</div>}
      {err && <div style={{ fontSize: 13, color: C.red, background: C.redBg, borderRadius: 7, padding: "10px 14px" }}>{err}</div>}
      {ans && (
        <div className="fade"><Panel>
          <div style={{ padding: 20 }}>
            {!ans.answered && <div style={{ fontSize: 10.5, letterSpacing: 1, textTransform: "uppercase", color: C.slate, marginBottom: 8, fontWeight: 600 }}>No grounded answer</div>}
            <p style={{ margin: "0 0 16px", fontSize: 14.5, lineHeight: 1.7 }}>{ans.text}</p>
            {ans.citations?.length > 0 && (
              <div style={{ borderTop: `1px solid ${C.line2}`, paddingTop: 13 }}>
                <div style={{ fontSize: 10, letterSpacing: 1, textTransform: "uppercase", color: C.faint, marginBottom: 9, fontWeight: 600 }}>Sources</div>
                {ans.citations.map((c, i) => (
                  <div key={i} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 0", borderBottom: i < ans.citations.length - 1 ? `1px solid ${C.line2}` : "none" }}>
                    <div><span className="mono" style={{ fontSize: 12.5, fontWeight: 600 }}>{c.source}</span>{c.section && <span style={{ fontSize: 12, color: C.muted }}> · {c.section}</span>}</div>
                    <span className="mono" style={{ fontSize: 11.5, color: C.amber, fontWeight: 600 }}>{c.similarity_score.toFixed(2)}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </Panel></div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// DOCS
// ---------------------------------------------------------------------------
function Docs() {
  const [docs, setDocs] = useState([]); const [loading, setLoading] = useState(true); const [err, setErr] = useState("");
  const [drag, setDrag] = useState(false); const [uploading, setUploading] = useState(false);
  const fileRef = useRef();

  async function load() {
    setLoading(true); setErr("");
    try { const d = await listDocuments(); setDocs(d.documents || []); } catch (e) { setErr(e.message); } finally { setLoading(false); }
  }
  useEffect(() => { load(); }, []);

  async function upload(files) {
    setUploading(true); setErr("");
    try { for (const f of files) await uploadDocument(f); await load(); }
    catch (e) { setErr(e.message); } finally { setUploading(false); }
  }

  return (
    <div style={{ maxWidth: 760 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
        <div style={{ fontSize: 13, color: C.muted }}>{loading ? "Loading…" : `${docs.length} documents in the knowledge base`}</div>
        <button className="btn" onClick={() => fileRef.current?.click()} disabled={uploading} style={{ background: C.ink, color: "#fff", border: "none", borderRadius: 7, padding: "8px 15px", fontSize: 12.5, fontWeight: 600 }}>{uploading ? "Uploading…" : "+ Add documents"}</button>
        <input ref={fileRef} type="file" multiple accept=".md,.txt" style={{ display: "none" }} onChange={e => { const f = Array.from(e.target.files || []); if (f.length) upload(f); }} />
      </div>
      <div onDragOver={e => { e.preventDefault(); setDrag(true); }} onDragLeave={() => setDrag(false)} onDrop={e => { e.preventDefault(); setDrag(false); const f = Array.from(e.dataTransfer.files || []); if (f.length) upload(f); }} onClick={() => fileRef.current?.click()}
        style={{ border: `1.5px dashed ${drag ? C.amber : C.line}`, background: drag ? C.amberBg : C.surface, borderRadius: 9, padding: 20, textAlign: "center", marginBottom: 16, cursor: "pointer", transition: "all .15s" }}>
        <div style={{ fontSize: 13, color: drag ? C.amber : C.muted, fontWeight: 500 }}>Drop .md or .txt files here, or click to browse</div>
        <div style={{ fontSize: 11.5, color: C.faint, marginTop: 4 }}>Uploaded documents are chunked, embedded, and added to the vector store</div>
      </div>
      {err && <div style={{ fontSize: 13, color: C.red, background: C.redBg, borderRadius: 7, padding: "10px 14px", marginBottom: 14 }}>{err}</div>}
      <Panel>
        {docs.length === 0 && !loading && <div style={{ padding: 24, textAlign: "center", fontSize: 13, color: C.muted }}>No documents yet. Upload some, or run the ingest script.</div>}
        {docs.map((name, i) => (
          <div key={i} style={{ display: "flex", alignItems: "center", gap: 12, padding: "13px 16px", borderBottom: i < docs.length - 1 ? `1px solid ${C.line2}` : "none" }}>
            <div style={{ width: 30, height: 30, borderRadius: 6, background: C.line2, display: "grid", placeItems: "center", color: C.amber, fontSize: 13 }}>◆</div>
            <div className="mono" style={{ fontSize: 12.5, fontWeight: 600 }}>{name}</div>
          </div>
        ))}
      </Panel>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Primitives
// ---------------------------------------------------------------------------
function Logo() {
  return <div style={{ width: 30, height: 30, borderRadius: 7, background: `linear-gradient(135deg, ${C.amber}, #B87A12)`, display: "grid", placeItems: "center", flexShrink: 0, boxShadow: "0 2px 6px rgba(217,151,30,.35)" }}><span style={{ color: C.sidebar, fontWeight: 700, fontSize: 16, fontFamily: "'IBM Plex Mono',monospace" }}>و</span></div>;
}
function NavItem({ icon, label, active, collapsed, onClick }) {
  return (
    <div className="navitem" onClick={onClick} style={{ display: "flex", alignItems: "center", gap: 11, padding: collapsed ? "10px 0" : "9px 12px", justifyContent: collapsed ? "center" : "flex-start", borderRadius: 7, marginBottom: 2, background: active ? C.sidebarHover : "transparent", color: active ? "#fff" : "#93A2B0", position: "relative" }}>
      {active && !collapsed && <span style={{ position: "absolute", left: 0, top: 8, bottom: 8, width: 2.5, background: C.amber, borderRadius: 2 }} />}
      <span style={{ fontSize: 14, color: active ? C.amber : "#7C8B99" }}>{icon}</span>
      {!collapsed && <span style={{ fontSize: 13, fontWeight: active ? 600 : 450 }}>{label}</span>}
    </div>
  );
}
function Panel({ children }) { return <div style={{ background: C.surface, border: `1px solid ${C.line}`, borderRadius: 10, overflow: "hidden" }}>{children}</div>; }
function Kpi({ label, value, delta, deltaState, state, spark }) {
  const col = state ? stateColor(state) : C.ink;
  return (
    <div className="kpi" style={{ background: C.surface, border: `1px solid ${C.line}`, borderRadius: 10, padding: "15px 16px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div style={{ fontSize: 11.5, color: C.muted, fontWeight: 500 }}>{label}</div>
        <Spark data={spark} color={col} />
      </div>
      <div className="mono" style={{ fontSize: 27, fontWeight: 700, color: col, lineHeight: 1.1, marginTop: 8 }}>{value}</div>
      <div style={{ fontSize: 11, color: stateColor(deltaState) || C.muted, marginTop: 5 }}>{delta}</div>
    </div>
  );
}
function Spark({ data, color }) {
  if (!data) return null;
  const w = 56, h = 22, max = Math.max(...data), min = Math.min(...data);
  const pts = data.map((v, i) => `${(i / (data.length - 1)) * w},${h - ((v - min) / (max - min || 1)) * h}`).join(" ");
  return <svg width={w} height={h} style={{ display: "block" }}><polyline points={pts} fill="none" stroke={color} strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" opacity=".8" /></svg>;
}
function MiniSelect({ value, onChange, options }) {
  return <select value={value} onChange={e => onChange(e.target.value)} style={{ fontSize: 11.5, color: C.ink2, border: `1px solid ${C.line}`, borderRadius: 6, padding: "5px 8px", background: C.surface, cursor: "pointer" }}>{options.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select>;
}
function StateTag({ state, label, big }) {
  return <span style={{ display: "inline-block", fontSize: big ? 11.5 : 10.5, fontWeight: 600, color: stateColor(state), background: stateBg(state), padding: big ? "4px 11px" : "2px 8px", borderRadius: 5, textTransform: label && label.length < 10 ? "capitalize" : "none" }}>{label}</span>;
}
function SlaTag({ sla, hours }) {
  if (sla === "breached") return <StateTag state="red" label="Breached" />;
  if (sla === "at_risk") return <StateTag state="amber" label={`${hours}h left`} />;
  return <span style={{ fontSize: 11, color: C.muted }}>{hours ? `${hours}h` : "—"}</span>;
}
function Spinner({ small }) {
  const sz = small ? 14 : 26;
  return <span className="spin" style={{ display: "inline-block", width: sz, height: sz, border: `2.5px solid ${C.line}`, borderTopColor: C.amber, borderRadius: "50%" }} />;
}