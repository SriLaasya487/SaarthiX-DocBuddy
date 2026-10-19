import { useEffect, useState } from "react";
import { api } from "../api.js";
import { t as tr } from "../translate.js";
import { confirmByVoice, speak } from "../voice.js";

// The "confirm centre": nothing scanned, spoken, or set up by family is saved until the elder says Yes (principle 4).
export default function Pending({ lang, onChange }) {
  const [items, setItems] = useState([]);
  const [props, setProps] = useState([]);
  const [svc, setSvc] = useState([]);
  const load = () => {
    api.get("/pending").then(setItems).catch(() => {}); api.get("/consents/proposals").then(setProps).catch(() => {});
    api.get("/services/pending").then(setSvc).catch(() => {}); onChange?.();
  };
  useEffect(load, []);

  const decide = async (p, yes) => { await api.post(`/pending/${p.id}`, { confirm: yes }); speak(yes ? "Saved." : "Okay, not saved.", lang); load(); };
  const ask = async (text, yes, no) => { const v = await confirmByVoice(text, lang); if (v === true) yes(); else if (v === false) no(); };

  return (
    <section className="stack">
      <h2>{tr("Please check", lang)}</h2>
      {!items.length && !props.length && !svc.length && <p className="note">{tr("Nothing is waiting for you.", lang)}</p>}
      {props.map((p) => (
        <div className="card stack" key={"p" + p.id}>
          <p>{p.speak}</p><p className="note">{p.items.map((i) => `${i.data_type} (${i.scope})`).join(", ")}{p.days ? ` · ${p.days} days` : ""}</p>
          <button className="big ok" onClick={async () => { await api.post(`/consents/proposals/${p.id}`, { approve: true }); load(); }}>{tr("Yes, I agree", lang)}</button>
          <button className="big" onClick={async () => { await api.post(`/consents/proposals/${p.id}`, { approve: false }); load(); }}>{tr("No", lang)}</button>
          <button className="big mic" onClick={() => ask(p.speak, async () => { await api.post(`/consents/proposals/${p.id}`, { approve: true }); load(); }, async () => { await api.post(`/consents/proposals/${p.id}`, { approve: false }); load(); })}>{tr("🎤 Answer by voice", lang)}</button>
        </div>
      ))}
      {svc.map((s) => (
        <div className="card stack" key={"s" + s.id}>
          <p>{s.speak}</p>
          <button className="big ok" onClick={async () => { await api.post(`/services/${s.id}`, { accept: true }); load(); }}>{tr("Yes", lang)}</button>
          <button className="big" onClick={async () => { await api.post(`/services/${s.id}`, { accept: false }); load(); }}>{tr("No", lang)}</button>
        </div>
      ))}
      {items.map((p) => (
        <div className="card stack" key={p.id}>
          <h3>{p.kind.replace("_", " ")}{p.proposed_by ? ` · from ${p.proposed_by}` : ""}</h3>
          <p>{p.readback}</p>
          <pre className="note">{JSON.stringify(p.payload.simple || p.payload, null, 1).slice(0, 400)}</pre>
          <button className="big ok" onClick={() => decide(p, true)}>{tr("Yes, save", lang)}</button>
          <button className="big" onClick={() => decide(p, false)}>{tr("No", lang)}</button>
          <button className="big mic" onClick={() => ask(p.readback, () => decide(p, true), () => decide(p, false))}>{tr("🎤 Answer by voice", lang)}</button>
        </div>
      ))}
    </section>
  );
}
