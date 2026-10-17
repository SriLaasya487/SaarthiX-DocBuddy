import { useEffect, useState } from "react";
import { api } from "../api.js";
import { speak } from "../voice.js";

export default function Daily({ lang }) {
  const [tab, setTab] = useState("learn");
  return <section className="stack"><h2>Learn & benefits</h2>
    <div className="sub"><button className={tab === "learn" ? "on" : ""} onClick={() => setTab("learn")}>Learn the phone</button><button className={tab === "schemes" ? "on" : ""} onClick={() => setTab("schemes")}>Government benefits</button></div>
    {tab === "learn" ? <Lessons lang={lang} /> : <Schemes lang={lang} />}</section>;
}

function Lessons({ lang }) {
  const [list, setList] = useState([]); const [l, setL] = useState(null); const [score, setScore] = useState(null);
  useEffect(() => { api.get("/lessons").then(setList); }, []);
  const open = async (id) => { const x = await api.get(`/lessons/${id}`); setL(x); setScore(null); speak(x.steps.join(" "), lang); };
  if (!l) return <>{list.map((x) => <button className="big" key={x.id} onClick={() => open(x.id)}>{x.title}</button>)}</>;
  return <><button className="back" onClick={() => setL(null)}>← All lessons</button><h3>{l.title}</h3><ol>{l.steps.map((s, i) => <li key={i}>{s}</li>)}</ol>
    {l.quiz.map((q, qi) => <div className="card stack" key={qi}><p><b>{q.q}</b></p>{q.options.map((o, oi) => <button className="big" key={oi} onClick={() => { const ok = oi === q.answer; setScore(ok); speak(ok ? "Correct! Well done." : "Not quite. Let us read the steps again.", lang); }}>{o}</button>)}</div>)}
    {score !== null && <p className={score ? "goodnews" : "error"}>{score ? "Correct!" : "Try again"}</p>}</>;
}

function Schemes({ lang }) {
  const [f, setF] = useState({ age: "", income: "", pensioner: false }); const [r, setR] = useState(null);
  return <><p>Tell me a little and I will list schemes you may be eligible for. Always confirm at the official office or website.</p>
    <label>Age<input type="number" value={f.age} onChange={(e) => setF({ ...f, age: e.target.value })} /></label>
    <label>Family income<select value={f.income} onChange={(e) => setF({ ...f, income: e.target.value })}><option value="">Not low</option><option value="low">Low income</option><option value="bpl">Below poverty line (BPL card)</option></select></label>
    <label className="chk"><input type="checkbox" checked={f.pensioner} onChange={(e) => setF({ ...f, pensioner: e.target.checked })} />I receive a pension</label>
    <button className="big primary" disabled={!f.age} onClick={async () => { const x = await api.get(`/schemes?age=${f.age}&income=${f.income}&pensioner=${f.pensioner}`); setR(x); speak(`I found ${x.matches.length} schemes.`, lang); }}>Show schemes</button>
    {r && <>{r.matches.map((s) => <div className="card" key={s.id}><h3>{s.name}</h3><p>{s.why}</p><p className="note">Documents: {s.docs.join(", ")} · Where: {s.where}{s.verify ? " · rules change, please verify" : ""}</p></div>)}<p className="note">{r.disclaimer}</p></>}</>;
}
