import { useEffect, useState } from "react";
import { api } from "../api.js";
import { bleSupported, readBloodPressure, readGlucose, readHeartRate, readSpO2 } from "../bluetooth.js";
import { canListen, confirmByVoice, listen, speak } from "../voice.js";

export default function Health({ lang }) {
  const [vitals, setVitals] = useState([]);
  const [appts, setAppts] = useState([]);
  const [card, setCard] = useState({ blood_group: "", allergies: "", doctor_phone: "", doctor_name: "", conditions: "", contacts: "" });
  const [msg, setMsg] = useState("");
  const [appt, setAppt] = useState({ doctor: "", at: "" });
  const [report, setReport] = useState(null);

  const load = () => { api.get("/vitals").then(setVitals); api.get("/appointments").then(setAppts); api.get("/emergency-card").then((c) => setCard((p) => ({ ...p, ...c }))); };
  useEffect(load, []);
  const say = (m) => { setMsg(m); speak(m, lang); };

  // DB-012/028: speak a reading -> server parses -> read back -> saved only after "yes"
  const byVoice = async () => {
    speak("Tell me your reading, like: B P is 140 over 90.", lang);
    await new Promise((r) => setTimeout(r, 3500));
    const t = await listen(lang).catch(() => "");
    const r = await api.post("/vitals/voice", { text: t });
    if (!r.understood) return say(r.speak);
    let yes = await confirmByVoice(r.speak, lang);
    if (yes === null) yes = window.confirm(r.speak);
    if (yes) { const s = await api.post(`/pending/${r.pending_id}`, { confirm: true }); say(s.flagged ? s.advice : "Saved."); } else await api.post(`/pending/${r.pending_id}`, { confirm: false });
    load();
  };
  const ble = async (fn) => {
    try {
      say("Start a measurement on your device now.");
      const r = await fn(); const { device, ...v } = r;
      if (!window.confirm(`Save ${v.kind.toUpperCase()} ${v.value1}${v.value2 ? "/" + v.value2 : ""}?`)) return;
      const out = await api.post("/devices/readings", { readings: [v] }); say(out.flagged ? "Saved. This reading is outside the usual range. Please tell your doctor." : "Saved."); load();
    } catch (e) { say(e.message || "Could not connect."); }
  };
  const openPrint = async () => window.open(await api.blob("/emergency-card/print"), "_blank");
  const weekly = async () => { const r = await api.get("/reports/week"); setReport(r); speak(`This week you took ${r.adherence_pct ?? "some"} percent of your medicines and checked in ${r.checkins} times.`, lang); };

  return (
    <section className="stack">
      <h2>Readings</h2>
      {canListen() && <button className="big mic" onClick={byVoice}>🎤 Say my BP or sugar</button>}
      {bleSupported() && <div className="sub"><button onClick={() => ble(readBloodPressure)}>Bluetooth BP</button><button onClick={() => ble(readGlucose)}>Bluetooth sugar</button>
        <button onClick={() => ble(readSpO2)}>Oxygen</button><button onClick={() => ble(readHeartRate)}>Pulse</button></div>}
      {msg && <p className="note" role="status">{msg}</p>}
      <div className="card">
        {vitals.slice(0, 6).map((v, i) => (
          <div className="row" key={i}><span>{v.kind.toUpperCase()} {v.value1}{v.value2 ? `/${v.value2}` : ""}{v.source !== "manual" && v.source !== "voice" ? ` (${v.source})` : ""}</span>
            <span className={v.flagged ? "warn" : ""}>{new Date(v.at + "Z").toLocaleDateString()}{v.flagged ? " ⚠" : ""}</span></div>
        ))}
        {!vitals.length && <p className="note">No readings yet.</p>}
      </div>

      <h2>My weekly report</h2>
      <button className="big" onClick={weekly}>🔊 Read my week</button>
      {report && <div className="card"><p>Medicines taken: <b>{report.adherence_pct ?? "–"}%</b> · Check-ins: {report.checkins} · Good days: {report.good_days}</p>{report.good_news?.map((g) => <p className="goodnews" key={g}>★ {g}</p>)}</div>}

      <h2>Doctor visits</h2>
      {appts.map((a) => <div className="row" key={a.id}><span>{a.doctor}{a.kind === "tele" ? " (video)" : ""}</span><span>{new Date(a.at + "Z").toLocaleString()}</span></div>)}
      <div className="card stack">
        <label>Doctor<input value={appt.doctor} onChange={(e) => setAppt({ ...appt, doctor: e.target.value })} /></label>
        <label>When<input type="datetime-local" value={appt.at} onChange={(e) => setAppt({ ...appt, at: e.target.value })} /></label>
        <button className="big" disabled={!appt.doctor || !appt.at} onClick={async () => { await api.post("/appointments", { ...appt, at: new Date(appt.at).toISOString().replace("Z", "") }); setAppt({ doctor: "", at: "" }); load(); }}>Add visit</button>
      </div>

      <h2>Emergency card</h2>
      <div className="card stack">
        {[["blood_group", "Blood group"], ["allergies", "Allergies"], ["conditions", "Health conditions"], ["doctor_name", "Doctor's name"], ["doctor_phone", "Doctor's phone"], ["contacts", "Emergency contacts (Name:phone; Name:phone)"]].map(([k, l]) => (
          <label key={k}>{l}<input value={card[k] || ""} onChange={(e) => setCard({ ...card, [k]: e.target.value })} /></label>))}
        <p className="note">Medicines are added automatically from your list.</p>
        <button className="big" onClick={async () => { const { medicines, ...c } = card; await api.put("/emergency-card", c); say("Card saved."); }}>Save card</button>
        <button className="big" onClick={openPrint}>🖨 Print for the fridge or wallet</button>
      </div>
    </section>
  );
}
