import { useEffect, useState } from "react";
import { api } from "../api.js";
import { canListen, dictate, speak } from "../voice.js";

const TABS = [["scam", "Is this a scam?"], ["find", "Hospital / medical shop"], ["weather", "Weather & air"], ["home", "Home safety"], ["help", "Helplines"], ["disaster", "Extra safety mode"]];
const pos = () => new Promise((ok, no) => navigator.geolocation.getCurrentPosition((p) => ok(p.coords), no, { timeout: 8000 }));

export default function SafetyHub({ lang }) {
  const [tab, setTab] = useState("scam");
  return (
    <section className="stack">
      <h2>Staying safe</h2>
      <div className="sub">{TABS.map(([k, l]) => <button key={k} className={tab === k ? "on" : ""} onClick={() => setTab(k)}>{l}</button>)}</div>
      {tab === "scam" && <Scam lang={lang} />}{tab === "find" && <Finder lang={lang} />}{tab === "weather" && <Weather lang={lang} />}
      {tab === "home" && <Home lang={lang} />}{tab === "help" && <Helplines lang={lang} />}{tab === "disaster" && <Disaster lang={lang} />}
    </section>
  );
}

function Scam({ lang }) {
  const [t, setT] = useState(""); const [r, setR] = useState(null); const [tip, setTip] = useState("");
  useEffect(() => { api.get("/scam/tips").then((x) => setTip(x.tip)); }, []);
  const check = async (text = t) => { const x = await api.post("/scam/check", { text, source: "message or call" }); setR(x); speak(`${x.level === "low" ? "I see no usual scam signs." : "Be careful! This looks like a scam."} ${x.advice}`, lang); };
  return <>
    <div className="card"><b>Tip of the day:</b> {tip}</div>
    <p>Got a strange message or call? Type or say what they said.</p>
    <textarea rows={4} value={t} onChange={(e) => setT(e.target.value)} placeholder="Your KYC is expiring. Share the OTP now…" />
    {canListen() && <button className="big mic" onClick={async () => { const x = await dictate(lang); if (x) { setT(x); check(x); } }}>🎤 Say what they said</button>}
    <button className="big primary" disabled={!t.trim()} onClick={() => check()}>Check</button>
    {r && <div className={"card " + (r.level === "low" ? "good" : "")}><h3 className={r.level === "low" ? "" : "warn"}>Risk: {r.level}</h3>{r.reasons.map((x) => <p key={x}>⚠ {x}</p>)}<p>{r.advice}</p>
      {r.ask_to_inform_alert_id && <><p>Shall I tell your family?</p><button className="big ok" onClick={async () => { await api.post(`/alerts/${r.ask_to_inform_alert_id}/respond`, { allow: true }); speak("I told them.", lang); }}>Yes</button>
        <button className="big" onClick={() => api.post(`/alerts/${r.ask_to_inform_alert_id}/respond`, { allow: false })}>No</button></>}
      <a className="big" href="tel:1930">Call cyber-crime helpline 1930</a></div>}
  </>;
}

function Finder({ lang }) {
  const [kind, setKind] = useState("pharmacy"); const [late, setLate] = useState(true); const [r, setR] = useState(null); const [err, setErr] = useState("");
  const go = async () => {
    setErr(""); try { const c = await pos(); setR(await api.get(`/finder/${kind}?lat=${c.latitude}&lng=${c.longitude}&late=${late}`)); } catch { setErr("I could not find your location. Please allow location access."); }
  };
  return <>
    <div className="grid2"><button className={"big " + (kind === "pharmacy" ? "primary" : "")} onClick={() => setKind("pharmacy")}>Medical shop</button><button className={"big " + (kind === "hospital" ? "primary" : "")} onClick={() => setKind("hospital")}>Hospital</button></div>
    <label className="chk"><input type="checkbox" checked={late} onChange={(e) => setLate(e.target.checked)} />Only places open late / 24 hours</label>
    <button className="big primary" onClick={go}>📍 Find near me</button>{err && <p className="error">{err}</p>}
    {r && <>{r.places.map((p, i) => <div className="card stack" key={i}><h3>{p.name} · {p.km} km</h3><p className="note">{p.hours || "hours not known"}{p.open_late ? " · open late" : ""}</p>
      <div className="grid2">{p.call && <a className="big" href={p.call}>Call</a>}<a className="big" href={p.directions} target="_blank" rel="noreferrer">Directions</a></div></div>)}
      <p className="note">{r.note}</p><a className="big" href={r.maps_link} target="_blank" rel="noreferrer">Open in Maps</a>
      <div className="grid2"><a className="big" href="tel:108">Ambulance 108</a><a className="big" href="tel:112">Emergency 112</a></div></>}
  </>;
}

function Weather({ lang }) {
  const [r, setR] = useState(null); const [err, setErr] = useState("");
  const go = async () => { try { const c = await pos(); const x = await api.get(`/weather/advice?lat=${c.latitude}&lng=${c.longitude}`); setR(x); speak(x.speak, lang); } catch { try { const x = await api.get("/weather/advice"); setR(x); speak(x.speak, lang); } catch { setErr("Please allow location access."); } } };
  useEffect(() => { go(); }, []);
  return <>{err && <p className="error">{err}</p>}{r && <div className="card stack"><h3>{r.temp_c ?? "?"}°C {r.aqi ? `· air quality ${r.aqi}` : ""}</h3>{r.advice.map((a) => <p key={a}>{a}</p>)}
    {r.suggest_disaster_mode && <button className="big ok" onClick={async () => { await api.post("/disaster", { on: true, kind: "heatwave" }); speak("Extra safety mode is on.", lang); }}>Turn on extra safety mode</button>}</div>}
    <button className="big" onClick={go}>Refresh</button></>;
}

function Home({ lang }) {
  const [r, setR] = useState(null); const load = () => api.get("/home-safety").then(setR); useEffect(() => { load(); }, []);
  if (!r) return null;
  return <><p>Go through your home with a family member. Tick what is already safe.</p><p><b>{r.score} of {r.total}</b> are safe.</p>
    {r.items.map((i) => <div className="row" key={i.id}><span>{i.text}</span><span><button onClick={async () => { setR(await api.post("/home-safety", { id: i.id, ok: true })); }}>{i.ok === true ? "✔" : "Yes"}</button>
      <button className={i.ok === false ? "stop" : ""} onClick={async () => { setR(await api.post("/home-safety", { id: i.id, ok: false })); }}>{i.ok === false ? "✘" : "No"}</button></span></div>)}
    {r.to_fix.length > 0 && <div className="card"><h3>To fix</h3>{r.to_fix.map((x) => <p key={x}>• {x}</p>)}</div>}</>;
}

function Helplines({ lang }) {
  const [h, setH] = useState([]); const [f, setF] = useState({ name: "", number: "" });
  const load = () => api.get("/helplines").then(setH); useEffect(() => { load(); }, []);
  return <>{h.map((x) => <div className="row" key={x.number + x.name}><span>{x.name}<br /><b>{x.number}</b></span><span><a className="big" style={{ display: "inline-block", width: "auto", minHeight: 0, padding: ".3rem 1rem" }} href={`tel:${x.number}`}>Call</a>
    {x.custom && <button className="stop" onClick={async () => { await api.del(`/helplines/${x.number}`); load(); }}>Remove</button>}</span></div>)}
    <div className="card stack"><h3>Add my own number</h3><label>Name<input value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} /></label>
      <label>Number<input value={f.number} inputMode="tel" onChange={(e) => setF({ ...f, number: e.target.value })} /></label>
      <button className="big" disabled={!f.name || !f.number} onClick={async () => { await api.post("/helplines", f); setF({ name: "", number: "" }); load(); }}>Add</button></div></>;
}

function Disaster({ lang }) {
  const [d, setD] = useState(null); const load = () => api.get("/disaster").then(setD); useEffect(() => { load(); }, []);
  const set = async (on, kind) => { const r = await api.post("/disaster", { on, kind }); setD(r); if (on) speak(r.speak, lang); };
  return <><p>During a flood, heatwave, cyclone or bad air, I check on you three times a day and show what to do.</p>
    {d?.on ? <div className="card stack"><h3 className="warn">Extra safety mode: {d.kind}</h3>{d.guidance.map((g) => <p key={g}>{g}</p>)}<p className="note">Check-in times: {d.checkin_times.join(", ")}</p>
      {d.helplines.map((h) => <a key={h.number} className="big" href={`tel:${h.number}`}>{h.name} {h.number}</a>)}<button className="big" onClick={() => set(false, d.kind)}>Turn off</button></div> :
      <div className="grid2">{["flood", "heatwave", "cyclone", "cold", "pollution"].map((k) => <button className="big" key={k} onClick={() => set(true, k)}>{k}</button>)}</div>}</>;
}
