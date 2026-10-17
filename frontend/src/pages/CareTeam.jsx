import { useEffect, useRef, useState } from "react";
import { api } from "../api.js";

const TABS = [["team", "Care team"], ["tasks", "Tasks"], ["costs", "Costs"], ["connect", "Call & messages"], ["nri", "Help from afar"], ["me", "Looking after me"], ["inbox", "Inbox"], ["nominee", "Nominee"]];
const ROLES = [["primary", "Main caregiver"], ["sibling", "Sibling / relative"], ["doctor", "Doctor"], ["neighbour", "Trusted neighbour"], ["chw", "Health worker"], ["grandchild", "Grandchild"], ["guardian", "Guardian"], ["nominee", "Nominee"]];

export default function CareTeam({ user, elder }) {
  const [tab, setTab] = useState("team"); const [msg, setMsg] = useState("");
  return (
    <section className="stack">
      <h2>Caring for {elder.name}</h2><p className="note">Their local time: {elder.local_time} ({elder.timezone})</p>
      <div className="sub">{TABS.map(([k, l]) => <button key={k} className={tab === k ? "on" : ""} onClick={() => setTab(k)}>{l}</button>)}</div>
      {msg && <p className="note" role="status">{msg}</p>}
      {tab === "team" && <Team user={user} elder={elder} say={setMsg} />}{tab === "tasks" && <Tasks elder={elder} say={setMsg} />}{tab === "costs" && <Costs user={user} elder={elder} say={setMsg} />}
      {tab === "connect" && <Connect elder={elder} say={setMsg} />}{tab === "nri" && <Nri elder={elder} say={setMsg} />}{tab === "me" && <Me say={setMsg} />}
      {tab === "inbox" && <Inbox />}{tab === "nominee" && <Nominee elder={elder} say={setMsg} />}
    </section>
  );
}

function Team({ user, elder, say }) {
  const [t, setT] = useState(null); const [f, setF] = useState({ phone: "", name: "", role: "sibling", relation: "" });
  const load = () => api.get(`/care-team?elder_id=${elder.id}`).then(setT).catch((e) => say(e.message)); useEffect(() => { load(); }, [elder.id]);
  return <>
    {t?.members.map((m) => <div className="row" key={m.id}><span>{m.name} · {m.role}{m.relation ? ` (${m.relation})` : ""}{t.responsible_this_week === m.id ? " · responsible this week" : ""}</span>
      <button onClick={async () => { try { await api.post("/care-team/handover", { elder_id: elder.id, responsible_id: m.id }); say("Handover saved."); load(); } catch (e) { say(e.message); } }}>This week</button></div>)}
    <div className="card stack"><h3>Suggest a new team member</h3><p className="note">{elder.name} must say yes before anything is shared. They will see your suggestion in “Please check”.</p>
      <label>Name<input value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} /></label><label>Mobile<input value={f.phone} inputMode="tel" onChange={(e) => setF({ ...f, phone: e.target.value })} /></label>
      <label>Role<select value={f.role} onChange={(e) => setF({ ...f, role: e.target.value })}>{ROLES.map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select></label>
      <label>What does {elder.name} call them?<input value={f.relation} onChange={(e) => setF({ ...f, relation: e.target.value })} /></label>
      <button className="big primary" disabled={!f.phone} onClick={async () => { try { await api.post("/care-team/invite", { elder_id: elder.id, member_phone: f.phone, member_name: f.name, role: f.role, relation: f.relation }); say("Suggestion sent. Waiting for their yes."); } catch (e) { say(e.message); } }}>Send suggestion</button></div>
    <p className="note">Remote setup: to set up medicines for {elder.name}, enter them on their phone's “Please check” list via the proposals above; nothing is saved without their yes.</p>
  </>;
}

function Tasks({ elder, say }) {
  const [rows, setRows] = useState([]); const [t, setT] = useState(""); const [due, setDue] = useState("");
  const load = () => api.get(`/tasks?elder_id=${elder.id}`).then(setRows).catch((e) => say(e.message)); useEffect(() => { load(); }, [elder.id]);
  const act = async (id, action) => { try { await api.post(`/tasks/${id}`, { action }); load(); } catch (e) { say(e.message); } };
  return <>{rows.map((r) => <div className="row" key={r.id}><span style={{ textDecoration: r.done ? "line-through" : "" }}>{r.title}{r.due_on ? ` · ${r.due_on}` : ""}{r.claimed_by ? ` · ${r.claimed_by}` : ""}</span>
    <span>{!r.done && !r.claimed_by && <button onClick={() => act(r.id, "claim")}>I'll do it</button>}{!r.done && r.claimed_by && <button onClick={() => act(r.id, "done")}>Done</button>}</span></div>)}
    <div className="card stack"><label>New task<input value={t} onChange={(e) => setT(e.target.value)} placeholder="Take Appa for eye check-up" /></label><label>By when<input type="date" value={due} onChange={(e) => setDue(e.target.value)} /></label>
      <button className="big primary" disabled={!t} onClick={async () => { try { await api.post("/tasks", { elder_id: elder.id, title: t, due_on: due || null }); setT(""); load(); } catch (e) { say(e.message); } }}>Add to board</button></div></>;
}

function Costs({ user, elder, say }) {
  const [d, setD] = useState(null); const [f, setF] = useState({ what: "", amount: "" });
  const load = () => api.get(`/expenses?elder_id=${elder.id}`).then(setD).catch((e) => say(e.message)); useEffect(() => { load(); }, [elder.id]);
  return <>{d && <><p>Total unsettled: <b>₹{d.total}</b></p>{d.items.map((i) => <div className="row" key={i.id}><span>{i.what}</span><b>₹{i.amount}</b></div>)}
    {d.settle_up.map((s, i) => <p className="goodnews" key={i}>User {s.from} pays user {s.to} ₹{s.amount}</p>)}</>}
    <div className="card stack"><label>What did you pay for?<input value={f.what} onChange={(e) => setF({ ...f, what: e.target.value })} /></label><label>Amount (₹)<input type="number" value={f.amount} onChange={(e) => setF({ ...f, amount: e.target.value })} /></label>
      <button className="big" disabled={!f.what || !f.amount} onClick={async () => { try { await api.post("/expenses", { elder_id: elder.id, what: f.what, amount: +f.amount }); setF({ what: "", amount: "" }); load(); } catch (e) { say(e.message); } }}>Add expense (split among the team)</button>
      <button className="big" onClick={async () => { await api.post(`/expenses/settle?elder_id=${elder.id}`); load(); }}>Mark all settled</button></div></>;
}

function Connect({ elder, say }) {
  const [nud, setNud] = useState([]); const [text, setText] = useState(""); const [rec, setRec] = useState(null); const [blob, setBlob] = useState(null); const [dg, setDg] = useState(null);
  useEffect(() => { api.get("/family/call-nudges").then(setNud); api.get(`/family/elders/${elder.id}/digest`).then(setDg).catch(() => {}); }, [elder.id]);
  const call = async () => { try { const r = await api.post(`/video/call/${elder.id}`); await api.post(`/family/elders/${elder.id}/called`); window.open(r.room_url, "_blank"); say(r.auto_answered ? "Connected - they pre-approved your calls." : "Ringing on their phone…"); } catch (e) { say(e.message); } };
  const rr = async () => { const ms = await navigator.mediaDevices.getUserMedia({ audio: true }); const mr = new MediaRecorder(ms); const ch = []; mr.ondataavailable = (e) => ch.push(e.data); mr.onstop = () => { ms.getTracks().forEach((t) => t.stop()); setBlob(new Blob(ch, { type: mr.mimeType })); }; mr.start(); setRec(mr); };
  const send = async () => { const b64 = blob ? await new Promise((res) => { const r = new FileReader(); r.onload = () => res(String(r.result).split(",")[1]); r.readAsDataURL(blob); }) : ""; try { await api.post("/messages", { elder_id: elder.id, kind: blob ? "voice" : "text", text, file_b64: b64 }); setText(""); setBlob(null); say("Sent."); } catch (e) { say(e.message); } };
  return <>
    {nud.filter((n) => n.elder_id === elder.id).map((n) => <div className="card" key={n.elder_id}><p>📞 {n.say} (it is {n.elder_local_time} there)</p></div>)}
    {dg && <div className="card"><h3>Good news</h3><p className="goodnews">{dg.say}</p></div>}
    <button className="big primary" onClick={call}>📹 Video call {elder.name}</button>
    <div className="card stack"><h3>Send a message (grandchildren love this)</h3><textarea rows={2} value={text} onChange={(e) => setText(e.target.value)} />
      {!rec || rec.state === "inactive" ? <button className="big mic" onClick={rr}>⏺ Record voice</button> : <button className="big" onClick={() => rec.stop()}>⏹ Stop</button>}
      {blob && <audio controls src={URL.createObjectURL(blob)} />}<button className="big" disabled={!text && !blob} onClick={send}>Send</button>
      <p className="note">Works only if {elder.name} allowed you to send messages.</p></div></>;
}

function Nri({ elder, say }) {
  const [f, setF] = useState({ kind: "nurse", when: "", amount: "", notes: "" }); const [r, setR] = useState(null);
  return <><p>Arrange local help from abroad. {elder.name} is asked first, because someone will come to the house.</p>
    <label>What help?<select value={f.kind} onChange={(e) => setF({ ...f, kind: e.target.value })}>{["nurse", "driver", "groceries", "other"].map((k) => <option key={k}>{k}</option>)}</select></label>
    <label>When (your time zone)<input type="datetime-local" value={f.when} onChange={(e) => setF({ ...f, when: e.target.value })} /></label><label>Amount (₹)<input type="number" value={f.amount} onChange={(e) => setF({ ...f, amount: e.target.value })} /></label>
    <label>Notes<input value={f.notes} onChange={(e) => setF({ ...f, notes: e.target.value })} /></label>
    <button className="big primary" disabled={!f.when} onClick={async () => { try { setR(await api.post("/services", { elder_id: elder.id, kind: f.kind, when: new Date(f.when).toISOString().replace("Z", ""), amount: +f.amount || 0, notes: f.notes })); } catch (e) { say(e.message); } }}>Request</button>
    {r && <div className="card"><p>Status: {r.status}. Visit at {r.elder_local_time} their time.</p>{r.payment_link && <a className="big" href={r.payment_link}>Pay ₹{f.amount}</a>}</div>}</>;
}

function Me({ say }) {
  const [q, setQ] = useState(null); const [a, setA] = useState([]); const [r, setR] = useState(null);
  useEffect(() => { api.get("/caregiver/wellbeing/questions").then((x) => { setQ(x); setA(x.questions.map(() => 0)); }); }, []);
  if (!q) return null;
  return <><p>Caring is hard. A quick check-in for you. ({q.scale})</p>{q.questions.map((x, i) => <label key={i}>{x}<select value={a[i]} onChange={(e) => setA(a.map((v, j) => (j === i ? +e.target.value : v)))}><option value={0}>Never</option><option value={1}>Sometimes</option><option value={2}>Often</option></select></label>)}
    <button className="big primary" onClick={async () => setR(await api.post("/caregiver/wellbeing", { answers: a }))}>See my result</button>
    {r && <div className={"card " + (r.level === "high" ? "" : "good")}><h3>{r.level} strain</h3>{r.tips.map((t) => <p key={t}>• {t}</p>)}<p className="note">{r.note}</p></div>}</>;
}

function Inbox() {
  const [rows, setRows] = useState([]); useEffect(() => { api.get("/inbox").then(setRows); }, []);
  return <>{!rows.length && <p className="note">No messages yet.</p>}{rows.map((n) => <div className="row" key={n.id}><span>{n.text}</span><span className="note">{new Date(n.at).toLocaleString()} · {n.channel}</span></div>)}</>;
}

function Nominee({ elder, say }) {
  const [reason, setReason] = useState(""); const [rid, setRid] = useState(""); const [log, setLog] = useState([]);
  return <><p>If {elder.name} cannot decide for themselves (for example, unconscious in hospital), a nominee they chose earlier can ask for limited health access. A doctor on the team AND a guardian or main caregiver must both approve. Everything is recorded, and {elder.name} can end it as soon as they are able.</p>
    <label>Reason<input value={reason} onChange={(e) => setReason(e.target.value)} /></label>
    <button className="big" disabled={!reason} onClick={async () => { try { const r = await api.post("/nominee/request", { elder_id: elder.id, reason }); say(`Request ${r.id} filed. ${r.needs}`); setRid(String(r.id)); } catch (e) { say(e.message); } }}>File request (nominee)</button>
    <label>Request number (to approve or view the record)<input value={rid} onChange={(e) => setRid(e.target.value)} /></label>
    <button className="big" disabled={!rid} onClick={async () => { try { const r = await api.post(`/nominee/${rid}/approve`); say(`Status: ${r.status}`); } catch (e) { say(e.message); } }}>Approve (doctor / guardian / main caregiver)</button>
    <button className="big" disabled={!rid} onClick={async () => setLog(await api.get(`/nominee/${rid}/audit`).catch(() => []))}>Show record</button>
    {log.map((l, i) => <p className="note" key={i}>{new Date(l.at + "Z").toLocaleString()} · {l.actor}: {l.what}</p>)}</>;
}
