import { useState } from "react";
import { api } from "../api.js";
import { canListen, confirmByVoice, dictate, speak } from "../voice.js";

// DB-067: small tasks by voice. The assistant PROPOSES an action; you confirm. It never pays, calls or sends alone.
export default function Assistant({ lang, onNavigate }) {
  const [log, setLog] = useState([]); const [t, setT] = useState("");
  const run = async (text) => {
    if (!text.trim()) return;
    const r = await api.post("/assistant/intent", { text });
    setLog((l) => [...l, ["me", text], ["bot", r.speak]]); setT("");
    const a = r.action; if (!a) return speak(r.speak, lang);
    let ok = true;
    if (a.needs_confirm) { ok = await confirmByVoice(r.speak, lang); if (ok === null) ok = window.confirm(r.speak); } else speak(r.speak, lang);
    if (!ok) return;
    if (a.type === "tel") window.location.href = a.href;
    else if (a.type === "link") window.open(a.href, "_blank");
    else if (a.type === "ui") onNavigate?.(a.route);
    else if (a.type === "alarm") { const d = new Date(); await api.post("/reminders", { kind: "alarm", title: "Alarm", due_on: d.toISOString().slice(0, 10), due_time: a.time }); speak(`Alarm set for ${a.time}.`, lang); }
    else if (a.type === "sos") { const x = await api.post("/sos", { location: "" }); speak(`I told ${x.contacts_notified} people. Please also call 112.`, lang); }
    else if (a.type === "imfine") { const x = await api.post("/imfine?approve=true"); speak(x.speak, lang); }
  };
  return (
    <section className="stack">
      <h2>Ask DocBuddy</h2>
      <p className="note">Try: “call my son”, “set alarm at 6 pm”, “bus to Charminar”, “pay my electricity bill”, “read the news”.</p>
      {log.map(([w, x], i) => <div className={"card " + (w === "bot" ? "good" : "")} key={i}><p>{x}</p></div>)}
      {canListen() && <button className="big mic" onClick={async () => run(await dictate(lang))}>🎤 Speak</button>}
      <input value={t} onChange={(e) => setT(e.target.value)} placeholder="Or type here" onKeyDown={(e) => e.key === "Enter" && run(t)} />
      <p className="note">For payments you always check the amount and enter your own PIN. DocBuddy never pays for you.</p>
    </section>
  );
}
