import { useState } from "react";
import { api } from "../api.js";
import { t as tr } from "../translate.js";
import { canListen, listen, speak } from "../voice.js";

export default function Doctor({ lang }) {
  const [text, setText] = useState("");
  const [res, setRes] = useState(null);

  const ask = async (t = text) => {
    const r = await api.post("/doctor/suggest", { symptom: t });
    setRes(r);
    speak(`You may meet a ${r.doctor}. ${r.why} ${r.urgent_note} ${r.disclaimer}`, lang);
  };
  const byVoice = async () => { const t = await listen(lang).catch(() => ""); if (t) { setText(t); ask(t); } };

  return (
    <section className="stack">
      <h2>{tr("Which doctor should I meet?", lang)}</h2>
      <p>{tr("Tell me what is bothering you.", lang)}</p>
      {canListen() && <button className="big mic" onClick={byVoice}>{tr("🎤 Speak", lang)}</button>}
      <label>{tr("Or type here", lang)}<textarea rows="3" value={text} onChange={(e) => setText(e.target.value)} /></label>
      <button className="big primary" disabled={!text} onClick={() => ask()}>{tr("Suggest a doctor", lang)}</button>
      {res && (
        <div className="card">
          <h3>{res.doctor}</h3>
          <p>{res.why}</p>
          {res.urgent_note && <p className="error">{res.urgent_note}</p>}
          <p className="note">{res.disclaimer}</p>
        </div>
      )}
    </section>
  );
}
