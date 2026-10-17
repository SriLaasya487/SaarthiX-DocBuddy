import { useEffect, useState } from "react";
import { api } from "../api.js";

// DB-087 (organisations), DB-088 (community health workers), DB-089 (aggregate insights)
export default function PartnerPortal({ user, onLogout }) {
  const [elders, setElders] = useState([]); const [sel, setSel] = useState(null); const [data, setData] = useState(null); const [msg, setMsg] = useState("");
  const [org, setOrg] = useState({ name: "", kind: "ngo" }); const [code, setCode] = useState(""); const [agg, setAgg] = useState(null);
  const [v, setV] = useState({ kind: "bp", value1: "", value2: "", notes: "", mood: "okay" });
  const load = () => api.get("/orgs/me/elders").then(setElders).catch(() => {}); useEffect(() => { load(); }, []);
  const open = async (id) => { setSel(id); setMsg(""); try { setData(await api.get(`/family/elders/${id}/summary`)); } catch (e) { setMsg(e.message); } };
  const visit = async () => {
    try {
      const body = { elder_id: sel, notes: v.notes, vitals: v.value1 ? [{ kind: v.kind, value1: +v.value1, value2: v.value2 ? +v.value2 : null }] : [], checkin: { mood: v.mood, note: v.notes } };
      const r = await api.post("/chw/visit", body); setMsg(`Saved: ${r.vitals} reading(s)${r.checkin ? " + check-in" : ""}. Recorded as made by you on the elder's behalf.`);
    } catch (e) { setMsg(e.message); }
  };
  return (
    <div className="shell wide">
      <header className="bar"><strong>AarogyaSaathi · {user.role === "chw" ? "Health worker" : "Organisation"}</strong><span className="tools"><span>{user.name}</span><button onClick={onLogout}>Sign out</button></span></header>
      <main className="page stack">
        {msg && <p className="note" role="status">{msg}</p>}
        {user.role === "partner" && <div className="card stack"><h3>Your organisation</h3>
          <label>Name<input value={org.name} onChange={(e) => setOrg({ ...org, name: e.target.value })} /></label>
          <label>Type<select value={org.kind} onChange={(e) => setOrg({ ...org, kind: e.target.value })}>{["ngo", "government", "hospital", "insurer", "pharmacy", "oldagehome", "corporate"].map((k) => <option key={k}>{k}</option>)}</select></label>
          <button className="big" disabled={!org.name} onClick={async () => { const r = await api.post("/orgs", org); setCode(r.code); }}>Create</button>
          {code && <p>Give this code to seniors: <b>{code}</b>. They choose exactly what you may see.</p>}
          <button className="big" onClick={async () => { try { setAgg(await api.get("/insights/aggregate")); } catch (e) { setMsg(e.message); } }}>Area statistics (anonymous)</button>
          {agg && <div className="card"><p className="note">{agg.note}</p>{agg.regions.map((r) => <div className="row" key={r.region}><span>{r.region} · {r.elders}+ people</span><span>low mood {r.low_mood_pct ?? "–"}% · flagged readings {r.flagged_reading_pct ?? "–"}%</span></div>)}{!agg.regions.length && <p>No area has enough people yet ({agg.suppressed_regions} hidden for privacy).</p>}</div>}</div>}
        <h3>People who shared with you</h3>
        {!elders.length && <p className="note">Nobody yet.</p>}
        <nav className="tabs">{elders.map((e) => <button key={e.id} className={sel === e.id ? "on" : ""} onClick={() => open(e.id)}>{e.name}</button>)}</nav>
        {data && <div className="card"><h3>Shared with you</h3><p>{Object.keys(data.shared).join(", ") || "nothing"}</p>{data.shared.report && <p>Adherence {data.shared.report.adherence_pct ?? "–"}% · check-ins {data.shared.report.checkins}</p>}</div>}
        {user.role === "chw" && sel && <div className="card stack"><h3>Home visit entry</h3><p className="note">Allowed only if the senior gave you permission to add readings. It is recorded as entered by you.</p>
          <label>Reading<select value={v.kind} onChange={(e) => setV({ ...v, kind: e.target.value })}>{["bp", "sugar", "spo2", "pulse"].map((k) => <option key={k}>{k}</option>)}</select></label>
          <label>Value<input value={v.value1} onChange={(e) => setV({ ...v, value1: e.target.value })} inputMode="decimal" /></label>{v.kind === "bp" && <label>Lower value<input value={v.value2} onChange={(e) => setV({ ...v, value2: e.target.value })} inputMode="decimal" /></label>}
          <label>Mood<select value={v.mood} onChange={(e) => setV({ ...v, mood: e.target.value })}><option>good</option><option>okay</option><option>low</option></select></label>
          <label>Notes<input value={v.notes} onChange={(e) => setV({ ...v, notes: e.target.value })} /></label><button className="big primary" onClick={visit}>Save visit</button></div>}
      </main>
    </div>
  );
}
