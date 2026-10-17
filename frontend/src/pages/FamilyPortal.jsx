import { useEffect, useState } from "react";
import { api } from "../api.js";
import CareTeam from "./CareTeam.jsx";

const LABEL = { mood: "Mood", checkins: "Daily check-ins", medicines: "Medicines", vitals: "Readings", emergency_card: "Emergency card", report: "Weekly report", imfine: "Today" };

export default function FamilyPortal({ user, onLogout }) {
  const [elders, setElders] = useState([]);
  const [sel, setSel] = useState(null);
  const [data, setData] = useState(null);
  const [err, setErr] = useState("");
  const [view, setView] = useState("overview");
  const [pre, setPre] = useState(null);

  useEffect(() => { api.get("/family/elders").then((e) => { setElders(e); if (e[0]) open(e[0].id); }); }, []);
  const open = async (id) => { setSel(id); setErr(""); setPre(null); try { setData(await api.get(`/family/elders/${id}/summary`)); } catch (e) { setErr(e.message); } };
  const elder = elders.find((e) => e.id === sel);
  const s = data?.shared || {};
  const previsit = async () => { try { setPre(await api.get(`/doctor/patients/${sel}/previsit`)); } catch (e) { setErr(e.message); } };

  return (
    <div className="shell wide">
      <header className="bar"><strong>DocBuddy · {user.role === "doctor" ? "Doctor" : "Family"}</strong><span className="tools"><button onClick={async () => { const r = await api.get("/inbox"); alert(r.slice(0, 8).map((n) => n.text).join("\n") || "No messages"); }}>Inbox</button><span>{user.name}</span><button onClick={onLogout}>Sign out</button></span></header>
      <main className="page">
        {elders.length === 0 && <p className="note">Nobody has shared anything with you yet. Ask your parent to add your mobile number under “Who can see what”.</p>}
        <nav className="tabs">{elders.map((e) => <button key={e.id} className={sel === e.id ? "on" : ""} onClick={() => open(e.id)}>{e.name} · {e.local_time}</button>)}</nav>
        {elder && <nav className="tabs"><button className={view === "overview" ? "on" : ""} onClick={() => setView("overview")}>Overview</button><button className={view === "care" ? "on" : ""} onClick={() => setView("care")}>Care team & tools</button></nav>}
        {err && <p className="error">{err}</p>}
        {view === "care" && elder && <CareTeam user={user} elder={elder} />}
        {view === "overview" && data && (
          <div className="family-grid">
            {"imfine" in s && <div className={"card " + (s.imfine ? "good" : "")}><h3>{LABEL.imfine}</h3><p>{s.imfine ? "✔ “I'm fine” today" : "No check-in yet today"}</p></div>}
            {s.report && <div className="card"><h3>{LABEL.report}</h3>
              <p>Medicine adherence: <b>{s.report.adherence_pct ?? "–"}%</b> ({s.report.doses_taken}/{s.report.doses_expected})</p>
              <p>Check-ins: {s.report.checkins} · Good days: {s.report.good_days}</p>
              {s.report.good_news.map((g) => <p className="goodnews" key={g}>★ {g}</p>)}</div>}
            {s.mood && <div className="card"><h3>{LABEL.mood}</h3><div className="moods">{s.mood.map((m, i) => <span key={i} title={m.at} className={"dot " + m.mood} />)}</div>
              {s.mood_trend?.note && <p className="note">{s.mood_trend.note}</p>}</div>}
            {s.checkins && <div className="card"><h3>{LABEL.checkins}</h3>{s.checkins.map((c, i) => <div className="row" key={i}><span>{new Date(c.at + "Z").toLocaleDateString()}</span><span>{c.mood}, pain {c.pain}{c.needs_help ? " · needed help" : ""}</span></div>)}</div>}
            {s.medicines && <div className="card"><h3>{LABEL.medicines}</h3>{s.medicines.map((m) => <div className="row" key={m.id}><span>{m.name} ×{m.tablets}</span>{m.low_stock && <b className="warn">low stock ({m.stock})</b>}</div>)}</div>}
            {s.vitals && <div className="card"><h3>{LABEL.vitals}</h3>{s.vitals.map((v, i) => <div className="row" key={i}><span>{v.kind.toUpperCase()} {v.value1}{v.value2 ? `/${v.value2}` : ""}</span>{v.flagged && <b className="warn">⚠</b>}</div>)}</div>}
            {s.appointments && <div className="card"><h3>Doctor visits</h3>{s.appointments.map((a, i) => <div className="row" key={i}><span>{a.doctor}{a.kind === "tele" ? " (video)" : ""}</span><span>{new Date(a.at + "Z").toLocaleString()}</span></div>)}</div>}
            {s.symptoms && <div className="card"><h3>Symptom diary</h3>{s.symptoms.map((x, i) => <p key={i}>{new Date(x.at + "Z").toLocaleDateString()}: {x.text}</p>)}</div>}
            {s.activity && <div className="card"><h3>Sleep & activity (7 days)</h3><p>Sleep: {s.activity.avg_sleep_hours ?? "–"} h · Steps: {s.activity.avg_steps ?? "–"} · Walks: {s.activity.walks}</p></div>}
            {s.cognitive && <div className="card"><h3>Memory exercises</h3>{s.cognitive.map((c, i) => <div className="row" key={i}><span>{new Date(c.at + "Z").toLocaleDateString()}</span><span>{c.score}/{c.max}</span></div>)}<p className="note">An exercise, not a diagnosis.</p></div>}
            {s.documents && <div className="card"><h3>Records</h3>{s.documents.map((d) => <p key={d.id}>📄 {d.kind}: {d.title}</p>)}</div>}
            {s.emergency_card && <div className="card"><h3>{LABEL.emergency_card}</h3><p>Blood group: {s.emergency_card.blood_group || "–"}</p><p>Allergies: {s.emergency_card.allergies || "–"}</p><p>Medicines: {s.emergency_card.medicines.join(", ") || "–"}</p></div>}
            {user.role === "doctor" && <div className="card stack"><h3>Pre-visit summary</h3><button className="big" onClick={previsit}>Open summary</button>
              {pre && <><p>Medicines: {pre.medicines.map((m) => m.name).join(", ")}</p>{pre.missed_doses.map((m) => <p className="warn" key={m.medicine}>Possibly missed: {m.medicine}</p>)}
                {pre.symptoms.map((x, i) => <p key={i}>{x.at}: {x.text}</p>)}{pre.vitals.map((v, i) => <p key={i}>{v.at} {v.kind} {v.value}{v.flagged ? " ⚠" : ""}</p>)}{pre.questions.map((q, i) => <p key={i}>❓ {q}</p>)}</>}</div>}
            {data.not_shared.length > 0 && <div className="card muted"><h3>Not shared with you</h3><p>{data.not_shared.join(", ")}</p></div>}
          </div>
        )}
      </main>
    </div>
  );
}
