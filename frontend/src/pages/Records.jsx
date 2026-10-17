import { useEffect, useRef, useState } from "react";
import { api } from "../api.js";
import { canListen, dictate, speak } from "../voice.js";

const TABS = [["diary", "Symptom diary"], ["visit", "Doctor visit"], ["notes", "After the visit"], ["labs", "Lab report"], ["locker", "My records"], ["vax", "Vaccines & check-ups"],
  ["tele", "Video doctor"], ["recovery", "Recovery"], ["insurance", "Insurance"]];
const b64 = (f) => new Promise((res) => { const r = new FileReader(); r.onload = () => res(String(r.result).split(",")[1]); r.readAsDataURL(f); });

export default function Records({ lang, onPending }) {
  const [tab, setTab] = useState("diary");
  const [msg, setMsg] = useState("");
  const say = (m) => { setMsg(m); speak(m, lang); };
  return (
    <section className="stack">
      <h2>My health records</h2>
      <div className="sub">{TABS.map(([k, l]) => <button key={k} className={tab === k ? "on" : ""} onClick={() => setTab(k)}>{l}</button>)}</div>
      {msg && <p className="note" role="status">{msg}</p>}
      {tab === "diary" && <Diary lang={lang} say={say} />}
      {tab === "visit" && <PreVisit lang={lang} say={say} />}
      {tab === "notes" && <VisitNotes lang={lang} say={say} onPending={onPending} />}
      {tab === "labs" && <Labs lang={lang} say={say} onPending={onPending} />}
      {tab === "locker" && <Locker lang={lang} say={say} />}
      {tab === "vax" && <Schedules lang={lang} say={say} />}
      {tab === "tele" && <Tele lang={lang} say={say} />}
      {tab === "recovery" && <Recovery lang={lang} say={say} />}
      {tab === "insurance" && <Insurance say={say} />}
    </section>
  );
}

function Mic({ lang, onText }) { return canListen() ? <button className="big mic" onClick={async () => { const t = await dictate(lang); if (t) onText(t); }}>🎤 Speak instead of typing</button> : null; }

function Diary({ lang, say }) {
  const [rows, setRows] = useState([]); const [t, setT] = useState("");
  const load = () => api.get("/symptoms").then(setRows); useEffect(() => { load(); }, []);
  const add = async (text = t) => { await api.post("/symptoms", { text }); setT(""); say("Written in your diary."); load(); };
  return <>
    <p>Tell me how you feel. I keep a diary so you can show your doctor.</p>
    <textarea rows={3} value={t} onChange={(e) => setT(e.target.value)} placeholder="My knee hurts at night…" />
    <Mic lang={lang} onText={(x) => add(x)} /><button className="big primary" disabled={!t.trim()} onClick={() => add()}>Add to diary</button>
    {rows.map((r) => <div className="row" key={r.id}><span>{new Date(r.at + "Z").toLocaleDateString()}: {r.text}</span><button className="stop" onClick={async () => { await api.del(`/symptoms/${r.id}`); load(); }}>Delete</button></div>)}
  </>;
}

function PreVisit({ lang, say }) {
  const [p, setP] = useState(null); const [q, setQ] = useState(""); const [doc, setDoc] = useState({ phone: "", name: "" });
  const load = () => api.get("/previsit").then(setP); useEffect(() => { load(); }, []);
  if (!p) return null;
  return <>
    <div className="card"><h3>Summary for your doctor (last {p.period_days} days)</h3>
      <p>Medicines: {p.medicines.map((m) => m.name).join(", ") || "none"}</p>
      {p.missed_doses.map((m) => <p className="warn" key={m.medicine}>Possibly missed: {m.medicine} (about {m.missed_approx})</p>)}
      <p>Symptoms noted: {p.symptoms.length} · Readings: {p.vitals.length} ({p.vitals.filter((v) => v.flagged).length} outside usual range) · Pain days: {p.pain_days}</p>
      {p.questions.map((x, i) => <p key={i}>❓ {x}</p>)}<p className="note">{p.disclaimer}</p></div>
    <label>Something to ask the doctor<input value={q} onChange={(e) => setQ(e.target.value)} /></label>
    <Mic lang={lang} onText={setQ} /><button className="big" disabled={!q} onClick={async () => { await api.post("/previsit/questions", { question: q }); setQ(""); load(); }}>Add question</button>
    <button className="big" onClick={async () => window.open(await api.blob("/previsit/print"), "_blank")}>🖨 Print summary</button>
    <div className="card stack"><h3>Share with my doctor for 7 days</h3>
      <label>Doctor's name<input value={doc.name} onChange={(e) => setDoc({ ...doc, name: e.target.value })} /></label>
      <label>Doctor's mobile<input value={doc.phone} onChange={(e) => setDoc({ ...doc, phone: e.target.value })} inputMode="tel" /></label>
      <button className="big" disabled={!doc.phone} onClick={async () => { const r = await api.post("/consents/share-with-doctor", { doctor_phone: doc.phone, doctor_name: doc.name, days: 7 }); say(`Shared with ${r.shared_with} for ${r.days} days. It stops by itself.`); }}>Share</button></div>
  </>;
}

function VisitNotes({ lang, say, onPending }) {
  const [t, setT] = useState(""); const [r, setR] = useState(null);
  return <>
    <p>After seeing the doctor, say what the doctor told you. I will write it in simple words and ask you to confirm.</p>
    <textarea rows={4} value={t} onChange={(e) => setT(e.target.value)} placeholder="Take the tablet after food twice daily. Avoid sweets. Come back after 2 weeks." />
    <Mic lang={lang} onText={setT} />
    <button className="big primary" disabled={!t.trim()} onClick={async () => { const x = await api.post("/visit-notes", { text: t }); setR(x); speak(x.speak, lang); onPending?.(); }}>Make it simple</button>
    {r && <div className="card"><p>{r.speak}</p><p className="note">Open “Please check” on the home screen to save it.</p></div>}
  </>;
}

function Labs({ lang, say, onPending }) {
  const [t, setT] = useState(""); const [r, setR] = useState(null); const f = useRef();
  const ocr = async (file) => { say("Reading the report. Please wait."); try { const T = await import("tesseract.js"); const { data } = await T.recognize(file, "eng"); setT(data.text); } catch { say("I could not read the photo. Please type the numbers."); } };
  return <>
    <input ref={f} type="file" accept="image/*" capture="environment" hidden onChange={(e) => e.target.files[0] && ocr(e.target.files[0])} />
    <button className="big mic" onClick={() => f.current.click()}>📷 Photo of my lab report</button>
    <textarea rows={5} value={t} onChange={(e) => setT(e.target.value)} placeholder="Hemoglobin 10.2 g/dL&#10;HbA1c 7.1 %" />
    <button className="big primary" disabled={!t.trim()} onClick={async () => { const x = await api.post("/labs/read?save=true", { text: t }); setR(x); speak(x.speak, lang); onPending?.(); }}>Explain in simple words</button>
    {r && <div className="card stack">{r.values.map((v) => <p key={v.test} className={v.position === "within the usual range" ? "" : "warn"}>{v.say}</p>)}<p className="note">{r.disclaimer}</p></div>}
  </>;
}

function Locker({ lang, say }) {
  const [docs, setDocs] = useState([]); const [q, setQ] = useState(""); const [found, setFound] = useState(null); const [exp, setExp] = useState([]);
  const [f, setF] = useState({ kind: "report", title: "", expires_on: "", file: null });
  const load = () => { api.get("/documents").then(setDocs); api.get("/documents/expiring").then(setExp); }; useEffect(() => { load(); }, []);
  const search = async (text = q) => { const r = await api.get(`/documents/search?q=${encodeURIComponent(text)}`); setFound(r); speak(r.speak, lang); };
  const add = async () => {
    await api.post("/documents", { kind: f.kind, title: f.title, expires_on: f.expires_on || null, file_b64: f.file ? await b64(f.file) : "", file_ext: f.file?.name.split(".").pop() || "jpg" });
    setF({ kind: "report", title: "", expires_on: "", file: null }); say("Saved in your records."); load();
  };
  return <>
    <div className="card stack"><label>Find something (try: show my last sugar test)<input value={q} onChange={(e) => setQ(e.target.value)} /></label>
      <Mic lang={lang} onText={(t) => { setQ(t); search(t); }} /><button className="big" onClick={() => search()}>Find</button>
      {found && <><p>{found.speak}</p>{found.documents.map((d) => <p key={d.id}>📄 {d.title}</p>)}</>}</div>
    {exp.length > 0 && <div className="card"><h3>Papers expiring soon</h3>{exp.map((d) => <p className="warn" key={d.id}>{d.title}: {d.days_left} days left</p>)}</div>}
    <div className="card stack"><h3>Add a document</h3>
      <label>Type<select value={f.kind} onChange={(e) => setF({ ...f, kind: e.target.value })}>{["prescription", "report", "lab", "scan", "aadhaar", "pan", "insurance", "pension", "other"].map((k) => <option key={k}>{k}</option>)}</select></label>
      <label>Name<input value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} /></label>
      <label>Expires / renews on (optional)<input type="date" value={f.expires_on} onChange={(e) => setF({ ...f, expires_on: e.target.value })} /></label>
      <label>Photo or PDF<input type="file" accept="image/*,application/pdf" onChange={(e) => setF({ ...f, file: e.target.files[0] })} /></label>
      <button className="big primary" disabled={!f.title} onClick={add}>Save</button></div>
    {docs.map((d) => <div className="row" key={d.id}><span>{d.kind}: {d.title}{d.expires_on ? ` · until ${d.expires_on}` : ""}</span><button className="stop" onClick={async () => { await api.del(`/documents/${d.id}`); load(); }}>Delete</button></div>)}
  </>;
}

function Schedules({ lang, say }) {
  const [v, setV] = useState([]); const [c, setC] = useState([]);
  const load = () => { api.get("/vaccinations").then((r) => setV(r.items)); api.get("/checkups").then((r) => setC(r.items)); }; useEffect(() => { load(); }, []);
  const Row = ({ i, path }) => <div className="row"><span className={i.overdue ? "warn" : ""}>{i.say}</span><button onClick={async () => { await api.post(path, { id: i.id }); say("Marked as done today."); load(); }}>Done today</button></div>;
  return <><p className="note">These are lists to talk about with your doctor, not medical advice.</p>
    <h3>Vaccines</h3>{v.map((i) => <Row key={i.id} i={i} path="/vaccinations/done" />)}<h3>Check-ups</h3>{c.map((i) => <Row key={i.id} i={i} path="/checkups/done" />)}</>;
}

function Tele({ lang, say }) {
  const [f, setF] = useState({ doctor: "", at: "" });
  return <>
    <p>Book a video visit. When it is time, one button opens the call.</p>
    <label>Doctor (leave empty for your family doctor)<input value={f.doctor} onChange={(e) => setF({ ...f, doctor: e.target.value })} /></label>
    <label>When<input type="datetime-local" value={f.at} onChange={(e) => setF({ ...f, at: e.target.value })} /></label>
    <button className="big" disabled={!f.at} onClick={async () => { try { await api.post("/teleconsult/book", { ...f, at: new Date(f.at).toISOString().replace("Z", "") }); say("Booked."); } catch (e) { say(e.message); } }}>Book video visit</button>
    <button className="big primary" onClick={async () => { const r = await api.get("/teleconsult/join"); r.join_url ? window.open(r.join_url, "_blank") : say(r.speak); }}>📹 Join my video visit now</button>
  </>;
}

function Recovery({ lang, say }) {
  const [p, setP] = useState(null); const [t, setT] = useState("");
  const load = () => api.get("/recovery").then(setP); useEffect(() => { load(); }, []);
  return <>
    <p>After a hospital stay, copy the doctor's instructions here, one per line. I turn them into a daily checklist. I add nothing of my own.</p>
    {p?.active ? <div className="card"><h3>{p.title} · until {p.ends}</h3>
      {p.today.map((i) => <label className="chk" key={i.id}><input type="checkbox" checked={i.done} onChange={async () => { await api.post("/recovery/tick", { item_id: i.id }); load(); }} />{i.text}</label>)}<p className="note">{p.speak}</p></div> : <>
      <textarea rows={5} value={t} onChange={(e) => setT(e.target.value)} placeholder={"Change dressing every morning\nSoft food for 3 days\nReview visit on day 7"} />
      <button className="big primary" disabled={!t.trim()} onClick={async () => { await api.post("/recovery", { items: t.split("\n").map((x) => x.trim()).filter(Boolean), days: 14 }); say("Your recovery checklist is ready."); load(); }}>Make my checklist</button></>}
  </>;
}

function Insurance({ say }) {
  const [r, setR] = useState(null); useEffect(() => { api.get("/insurance").then(setR); }, []);
  if (!r) return null;
  return <>{r.policies.map((p) => <div className="row" key={p.id}><span>{p.title}</span><span className={p.days_to_renewal != null && p.days_to_renewal < 30 ? "warn" : ""}>{p.days_to_renewal != null ? `renews in ${p.days_to_renewal} days` : "no date"}</span></div>)}
    {!r.policies.length && <p className="note">Add your policy in “My records” (type: insurance) with its renewal date.</p>}
    <div className="card"><h3>How to make a claim</h3><ol>{r.claim_steps.map((s, i) => <li key={i}>{s}</li>)}</ol><p className="note">{r.note}</p></div></>;
}
