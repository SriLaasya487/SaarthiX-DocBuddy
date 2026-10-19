import { useEffect, useRef, useState } from "react";
import { api } from "../api.js";
import { speak } from "../voice.js";
import { t as tr } from "../translate.js";
import { analyse } from "../pillvision.js";

export default function Medicines({ lang, onPending }) {
  const [due, setDue] = useState([]);
  const [all, setAll] = useState([]);
  const [form, setForm] = useState({ name: "", tablets: 1, times: "08:00,20:00", stock: 30, color: "" });
  const [adding, setAdding] = useState(false);
  const [msg, setMsg] = useState("");
  const [rx, setRx] = useState("");
  const [pill, setPill] = useState(null);
  const file = useRef(); const photo = useRef();

  const load = () => { api.get("/medicines/due").then(setDue); api.get("/medicines").then(setAll); };
  useEffect(load, []);
  useEffect(() => { if (due[0]) speak(tr("Time for {name}. Tap I took it when done.", lang, { name: due[0].name }), lang); }, [due.length]);
  const say = (m) => { setMsg(m); speak(m, lang); };

  const took = async (d) => { const r = await api.post(`/medicines/${d.medicine_id}/taken`, { slot: d.slot }); say(r.queued ? "Saved on this phone. It will sync when the network returns." : tr("Thank you. Noted.", lang)); load(); };
  const snooze = async (d) => { const r = await api.post(`/medicines/${d.medicine_id}/snooze`, { slot: d.slot, minutes: 10 }); say(tr("I will remind you in 10 minutes.", lang) + (r.offer_tell_family ? " You have snoozed a few times. You can ask family for help." : "")); load(); };
  const missed = async (d) => say((await api.post(`/medicines/${d.medicine_id}/missed`, { slot: d.slot })).speak);
  const add = async () => { await api.post("/medicines", { ...form, tablets: +form.tablets, stock: +form.stock }); setAdding(false); load(); };

  const interactions = async () => say((await api.get("/medicines/interactions")).speak);
  const generic = async (m) => say((await api.get(`/medicines/generic/${encodeURIComponent(m.name)}`)).say);
  const refill = async (m, channel) => {
    const r = await api.post("/refills", { medicine_id: m.id, channel });
    if (window.confirm(r.speak)) { const c = await api.post(`/refills/${r.id}/confirm`); say(c.note); if (c.open) window.open(c.open, "_blank"); }
  };

  // DB-018: photo -> OCR on the phone (tesseract.js, loaded only when used) -> candidates wait in the confirm centre
  const scan = async (f) => {
    if (!f) return;
    say("Reading your prescription. Please wait.");
    try {
      const T = await import("tesseract.js");
      const { data } = await T.recognize(f, "eng");
      setRx(data.text); await parse(data.text);
    } catch { say("I could not read the photo. You can type or paste the text below."); }
  };
  const parse = async (text) => {
    const r = await api.post("/prescriptions/parse", { text });
    say(r.candidates.length ? `I found ${r.candidates.length} medicine lines. Please check each one.` : "I could not find medicines in that text.");
    if (r.candidates.length) onPending?.();
  };

  // DB-034: photo of the pillbox -> count + colours -> compared with today's schedule
  const checkPills = async (f) => {
    if (!f) return;
    const a = await analyse(f);
    const r = await api.post("/pillbox/verify", { counts: a.counts });
    setPill({ ...r, seen: a }); speak(r.speak, lang);
  };

  return (
    <section className="stack">
      <h2>{tr("Medicines", lang)}</h2>
      {msg && <p className="note" role="status">{msg}</p>}
      {due.length === 0 && <p className="note">{tr("Nothing due right now. 🎉", lang)}</p>}
      {due.map((d) => (
        <div className="card stack" key={d.medicine_id + d.slot}>
          <h3>{d.name}</h3><p>{d.tablets} tablet{d.tablets > 1 ? "s" : ""} · {d.slot}{d.snoozed ? ` · reminded ${d.snoozed}×` : ""}</p>
          <button className="big ok" onClick={() => took(d)}>{tr("I took it", lang)}</button>
          <button className="big" onClick={() => snooze(d)}>{tr("Remind me in 10 minutes", lang)}</button>
          <button className="big" onClick={() => missed(d)}>{tr("I missed an earlier dose", lang)}</button>
          {d.offer_tell_family && <p className="note">Would you like family to give you a call? Use “Who can see what” → alerts, or press SOS if you need help.</p>}
        </div>
      ))}

      <h3>{tr("All my medicines", lang)}</h3>
      {all.map((m) => (
        <div className="card stack" key={m.id}>
          <div className="row"><span>{m.name} — {m.tablets}× at {m.times.join(", ")}{m.color ? ` · ${m.color}` : ""}</span>{m.low_stock && <b className="warn">Running low ({m.days_left} days)</b>}</div>
          <div className="sub">
            <button onClick={() => generic(m)}>Cheaper version?</button>
            <button onClick={() => refill(m, "whatsapp")}>Order more (WhatsApp)</button>
            <button onClick={() => refill(m, "1mg")}>1mg</button><button onClick={() => refill(m, "pharmeasy")}>PharmEasy</button>
          </div>
        </div>
      ))}
      {all.length > 1 && <button className="big" onClick={interactions}>Check my medicines together</button>}

      <h3>{tr("Add medicines", lang)}</h3>
      <input ref={file} type="file" accept="image/*" capture="environment" hidden onChange={(e) => scan(e.target.files[0])} />
      <button className="big mic" onClick={() => file.current.click()}>📷 Scan a prescription</button>
      <label>…or paste / type the prescription text<textarea rows={3} value={rx} onChange={(e) => setRx(e.target.value)} placeholder="Tab Metformin 500mg 1-0-1 x 30 days" /></label>
      <button className="big" disabled={!rx.trim()} onClick={() => parse(rx)}>Read this text</button>
      {!adding ? <button className="big" onClick={() => setAdding(true)}>+ Add by typing</button> : (
        <div className="card stack">
          <label>Medicine name<input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></label>
          <label>Tablets each time<input type="number" min="1" value={form.tablets} onChange={(e) => setForm({ ...form, tablets: e.target.value })} /></label>
          <label>Times (24h, comma separated)<input value={form.times} onChange={(e) => setForm({ ...form, times: e.target.value })} /></label>
          <label>Tablets in stock<input type="number" value={form.stock} onChange={(e) => setForm({ ...form, stock: e.target.value })} /></label>
          <label>Tablet colour (for the pillbox photo check)<select value={form.color} onChange={(e) => setForm({ ...form, color: e.target.value })}>
            {["", "white", "yellow", "pink", "red", "orange", "blue", "green", "brown"].map((c) => <option key={c} value={c}>{c || "not sure"}</option>)}</select></label>
          <button className="big primary" disabled={!form.name} onClick={add}>Save</button>
        </div>
      )}

      <h3>Pillbox check</h3>
      <input ref={photo} type="file" accept="image/*" capture="environment" hidden onChange={(e) => checkPills(e.target.files[0])} />
      <button className="big mic" onClick={() => photo.current.click()}>📷 Photo of my tablets</button>
      <p className="note">Place the tablets on a plain plate or paper, in good light.</p>
      {pill && <div className={"card " + (pill.ok ? "good" : "")}><p>{pill.speak}</p><p className="note">Seen: {JSON.stringify(pill.seen.counts)} · {pill.note}</p></div>}
    </section>
  );
}
