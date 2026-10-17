import { useEffect, useRef, useState } from "react";
import { api } from "../api.js";
import { canListen, dictate, speak } from "../voice.js";

const TABS = [["today", "Today"], ["talk", "Talk to me"], ["music", "Music & prayer"], ["news", "News"], ["calm", "Calm"], ["games", "Brain games"], ["memory", "Memory check"], ["stories", "My stories"], ["messages", "Messages"]];

export default function Companion({ lang }) {
  const [tab, setTab] = useState("today");
  return (
    <section className="stack">
      <h2>Companion</h2>
      <div className="sub">{TABS.map(([k, l]) => <button key={k} className={tab === k ? "on" : ""} onClick={() => setTab(k)}>{l}</button>)}</div>
      {tab === "today" && <Today lang={lang} />}{tab === "talk" && <Talk lang={lang} />}{tab === "music" && <Music lang={lang} />}{tab === "news" && <News lang={lang} />}
      {tab === "calm" && <Calm lang={lang} />}{tab === "games" && <Games lang={lang} />}{tab === "memory" && <Memory lang={lang} />}{tab === "stories" && <Stories lang={lang} />}{tab === "messages" && <Messages lang={lang} />}
    </section>
  );
}

function Today({ lang }) {
  const [rem, setRem] = useState([]); const [pat, setPat] = useState([]); const [mood, setMood] = useState(null); const [bd, setBd] = useState({ title: "", due_on: "" });
  const load = () => { api.get("/reminders/today").then((r) => { setRem(r); if (r[0]) speak(r.map((x) => x.say).join(" "), lang); }); api.get("/insights/patterns").then((r) => setPat(r.patterns)); api.get("/insights/mood").then(setMood); };
  useEffect(() => { load(); }, []);
  return <>
    {rem.map((r, i) => <div className="card good" key={i}><p>🎉 {r.say}</p></div>)}
    {!rem.length && <p className="note">No special days today.</p>}
    {pat.map((p) => <div className="card" key={p}><p>{p}</p></div>)}
    {mood?.note && <div className="card"><p>{mood.note}</p></div>}
    {mood?.series?.length > 0 && <div className="card"><h3>My mood, week by week</h3>{mood.series.map((s) => <div className="row" key={s.weeks_ago}><span>{s.weeks_ago === 0 ? "This week" : `${s.weeks_ago} week(s) ago`}</span><span>{"●".repeat(Math.max(1, Math.round(s.avg + 1)))}</span></div>)}</div>}
    <div className="card stack"><h3>Remember a birthday</h3>
      <label>Whose birthday?<input value={bd.title} onChange={(e) => setBd({ ...bd, title: e.target.value })} /></label>
      <label>Date of birth<input type="date" value={bd.due_on} onChange={(e) => setBd({ ...bd, due_on: e.target.value })} /></label>
      <button className="big" disabled={!bd.title || !bd.due_on} onClick={async () => { await api.post("/reminders", { kind: "birthday", title: bd.title, due_on: bd.due_on, yearly: true }); setBd({ title: "", due_on: "" }); speak("I will wish them with you.", lang); }}>Save</button></div>
  </>;
}

function Talk({ lang }) {
  const [log, setLog] = useState([]); const [t, setT] = useState("");
  const send = async (text) => { if (!text.trim()) return; const r = await api.post("/companion/chat", { text }); setLog((l) => [...l, ["me", text], ["bot", r.reply]]); setT(""); speak(r.reply, lang); };
  return <>
    {log.map(([w, x], i) => <div key={i} className={"card " + (w === "bot" ? "good" : "")}><p>{w === "bot" ? "DocBuddy: " : "You: "}{x}</p></div>)}
    {canListen() && <button className="big mic" onClick={async () => send(await dictate(lang))}>🎤 Talk</button>}
    <input value={t} onChange={(e) => setT(e.target.value)} placeholder="Or type here" onKeyDown={(e) => e.key === "Enter" && send(t)} />
    <p className="note">DocBuddy is a friendly companion. It cannot give medical advice.</p>
  </>;
}

function Music({ lang }) {
  const [m, setM] = useState(null); const [d, setD] = useState(null); const [faith, setFaith] = useState("");
  useEffect(() => { api.get("/companion/music").then(setM); }, []); useEffect(() => { api.get(`/devotional?faith=${faith}`).then(setD); }, [faith]);
  return <>
    {m && <a className="big" href={m.open} target="_blank" rel="noreferrer">🎵 Old songs in my language</a>}
    <label>Prayer & devotion<select value={faith} onChange={(e) => setFaith(e.target.value)}>{["", "hindu", "sikh", "muslim", "christian", "buddhist", "jain"].map((f) => <option key={f} value={f}>{f || "my usual"}</option>)}</select></label>
    {d?.prayer_times && <div className="card"><h3>Prayer times (approximate)</h3>{Object.entries(d.prayer_times).filter(([k]) => k !== "note").map(([k, v]) => <div className="row" key={k}><span>{k}</span><b>{v}</b></div>)}<p className="note">{d.prayer_times.note}</p></div>}
    {d?.items.map((i) => <a className="big" key={i.title} href={i.open} target="_blank" rel="noreferrer">{i.title}</a>)}
  </>;
}

function News({ lang }) {
  const [n, setN] = useState(null); useEffect(() => { api.get("/news").then(setN); }, []);
  if (!n) return <p className="note">Loading…</p>;
  return <><button className="big primary" onClick={() => speak(n.speak, lang)}>🔊 Read the news to me</button>
    {n.headlines.map((h, i) => <div className="card" key={i}><p>{h}</p></div>)}{n.today_in_history && <div className="card"><h3>Today in history</h3><p>{n.today_in_history}</p></div>}</>;
}

function Calm({ lang }) {
  const [b, setB] = useState(null); const [steps, setSteps] = useState(null); const [phase, setPhase] = useState("rest"); const [i, setI] = useState(0); const stop = useRef(false);
  useEffect(() => { api.get("/calm/breathing").then(setB); }, []);
  const tone = (f) => { try { const c = new (window.AudioContext || window.webkitAudioContext)(); const o = c.createOscillator(), g = c.createGain(); o.frequency.value = f; g.gain.value = 0.05; o.connect(g); g.connect(c.destination); o.start(); setTimeout(() => { o.stop(); c.close(); }, 400); } catch { /* no audio */ } };
  const breathe = async () => {
    stop.current = false; const p = b.pattern;
    for (let r = 0; r < b.rounds && !stop.current; r++) for (const [ph, sec, f] of [["in", p.in, 440], ["hold", p.hold, 330], ["out", p.out, 262]]) {
      if (stop.current) break; setPhase(ph); tone(f); if (r === 0) speak({ in: "Breathe in", hold: "Hold gently", out: "Breathe out slowly" }[ph], lang); await new Promise((res) => setTimeout(res, sec * 1000));
    }
    setPhase("rest");
  };
  const scale = phase === "in" ? 1.6 : phase === "hold" ? 1.6 : 1;
  return <>
    <p>Slow breathing helps the body relax. Follow the circle. It grows when you breathe in and shrinks when you breathe out.</p>
    <div className="breath" style={{ transform: `scale(${scale})`, transitionDuration: `${phase === "in" ? b?.pattern.in : phase === "out" ? b?.pattern.out : 0.3}s` }} aria-live="polite" />
    <p style={{ textAlign: "center" }}><b>{{ in: "Breathe in", hold: "Hold", out: "Breathe out", rest: "Ready" }[phase]}</b></p>
    {b && <><button className="big primary" onClick={breathe}>Start breathing</button><button className="big" onClick={() => { stop.current = true; }}>Stop</button></>}
    <button className="big" onClick={async () => { const r = await api.get("/calm/steps"); setSteps(r); setI(0); speak(r.steps[0], lang); }}>I feel worried or anxious</button>
    {steps && <div className="card stack"><p style={{ fontSize: "1.3rem" }}>{steps.steps[i]}</p>
      {i < steps.steps.length - 1 ? <button className="big primary" onClick={() => { setI(i + 1); speak(steps.steps[i + 1], lang); }}>Next</button> : <a className="big" href={`tel:${steps.helpline.number}`}>Call {steps.helpline.name} {steps.helpline.number}</a>}
      <p className="note">{steps.note}</p></div>}
  </>;
}

function Games({ lang }) {
  const [list, setList] = useState({}); const [g, setG] = useState(null); useEffect(() => { api.get("/games").then(setList); }, []);
  const start = async (k) => setG(await api.get(`/games/${k}/round`));
  const done = async (pct) => { const r = await api.post(`/games/${g.game}/score`, { level: g.level, pct }); speak(pct >= 80 ? "Wonderful!" : "Well tried. Let us try again.", lang); setG(null); };
  if (g) return g.game === "pairs" ? <Pairs g={g} done={done} /> : g.game === "sequence" ? <Sequence g={g} done={done} /> : <Words g={g} done={done} lang={lang} />;
  return <><p>Gentle games that get a little harder as you improve. There is no winning or losing.</p>{Object.entries(list).map(([k, n]) => <button className="big" key={k} onClick={() => start(k)}>{n}</button>)}</>;
}
function Pairs({ g, done }) {
  const [cards] = useState(() => [...g.symbols, ...g.symbols].map((s, i) => ({ s, i })).sort(() => Math.random() - 0.5));
  const [open, setOpen] = useState([]); const [got, setGot] = useState([]); const [tries, setTries] = useState(0);
  const flip = (c) => {
    if (open.length === 2 || open.includes(c.i) || got.includes(c.s)) return;
    const o = [...open, c.i]; setOpen(o);
    if (o.length === 2) { setTries((t) => t + 1); const [a, b] = o.map((x) => cards.find((k) => k.i === x)); setTimeout(() => { if (a.s === b.s) { const ng = [...got, a.s]; setGot(ng); if (ng.length === g.symbols.length) done(Math.max(20, Math.round(100 * g.symbols.length / (tries + 1)))); } setOpen([]); }, 700); }
  };
  return <div className="pairs">{cards.map((c) => <button key={c.i} onClick={() => flip(c)}>{open.includes(c.i) || got.includes(c.s) ? c.s : "?"}</button>)}</div>;
}
function Sequence({ g, done }) {
  const COLORS = ["#c62828", "#1f7a4d", "#1565c0", "#f2a900"]; const [lit, setLit] = useState(-1); const [phase, setPhase] = useState("watch"); const [step, setStep] = useState(0); const [ok, setOk] = useState(0);
  useEffect(() => { (async () => { for (const s of g.sequence) { await new Promise((r) => setTimeout(r, 450)); setLit(s); await new Promise((r) => setTimeout(r, 600)); setLit(-1); } setPhase("you"); })(); }, []);
  const tap = (i) => { if (phase !== "you") return; const good = g.sequence[step] === i; const o = ok + (good ? 1 : 0); if (step + 1 === g.sequence.length) return done(Math.round((100 * o) / g.sequence.length)); setOk(o); setStep(step + 1); };
  return <><p>{phase === "watch" ? "Watch the colours…" : `Now repeat them (${step + 1}/${g.sequence.length})`}</p><div className="pad">{COLORS.map((c, i) => <button key={i} style={{ background: c, opacity: lit === i ? 1 : 0.45 }} onClick={() => tap(i)} aria-label={`colour ${i + 1}`} />)}</div></>;
}
function Words({ g, done, lang }) {
  const [phase, setPhase] = useState("show"); const [t, setT] = useState("");
  useEffect(() => { speak(g.words.join(", "), lang); const id = setTimeout(() => setPhase("ask"), 2500 + g.words.length * 1200); return () => clearTimeout(id); }, []);
  if (phase === "show") return <div className="card"><h3>Remember these words</h3><p style={{ fontSize: "1.5rem" }}>{g.words.join(" · ")}</p></div>;
  const check = () => { const said = t.toLowerCase().split(/[ ,]+/); done(Math.round((100 * g.words.filter((w) => said.includes(w)).length) / g.words.length)); };
  return <><p>Which words do you remember?</p><textarea rows={3} value={t} onChange={(e) => setT(e.target.value)} />{canListen() && <button className="big mic" onClick={async () => setT(await dictate(lang))}>🎤 Say them</button>}<button className="big primary" onClick={check}>Done</button></>;
}

function Memory({ lang }) {
  const [s, setS] = useState(null); const [f, setF] = useState({ day: "", month: "", year: "", recall: "", backwards: "" }); const [r, setR] = useState(null);
  const start = async () => { const x = await api.get("/cognitive/start"); setS(x); setR(null); speak(x.steps.join(" "), lang); };
  const submit = async () => { const x = await api.post("/cognitive/submit", { ...f, words: s.words, digits: s.digits }); setR(x); speak(x.speak, lang); };
  return <>
    <p>A friendly brain exercise. It is <b>not a test for any illness</b>.</p>
    {!s && <button className="big primary" onClick={start}>Begin</button>}
    {s && !r && <div className="card stack">{s.steps.map((x, i) => <p key={i}>{i + 1}. {x}</p>)}
      <label>Today is (day of the week)<input value={f.day} onChange={(e) => setF({ ...f, day: e.target.value })} /></label>
      <label>Month<input value={f.month} onChange={(e) => setF({ ...f, month: e.target.value })} /></label>
      <label>Year<input value={f.year} onChange={(e) => setF({ ...f, year: e.target.value })} /></label>
      <label>Numbers backwards<input value={f.backwards} onChange={(e) => setF({ ...f, backwards: e.target.value })} /></label>
      <label>The three words<input value={f.recall} onChange={(e) => setF({ ...f, recall: e.target.value })} /></label>
      <button className="big primary" onClick={submit}>Finish</button></div>}
    {r && <div className="card stack"><h3>{r.score} / {r.max}</h3><p>{r.speak}</p><p className="note">{r.disclaimer}</p>
      {r.ask_to_inform_alert_id && <><button className="big ok" onClick={async () => { await api.post(`/alerts/${r.ask_to_inform_alert_id}/respond`, { allow: true }); speak("I told them.", lang); }}>Yes, tell them</button>
        <button className="big" onClick={async () => { await api.post(`/alerts/${r.ask_to_inform_alert_id}/respond`, { allow: false }); }}>No, keep it private</button></>}</div>}
  </>;
}

function Stories({ lang }) {
  const [rows, setRows] = useState([]); const [title, setTitle] = useState(""); const [rec, setRec] = useState(null); const [blob, setBlob] = useState(null); const [tx, setTx] = useState("");
  const load = () => api.get("/life-stories").then(setRows); useEffect(() => { load(); }, []);
  const start = async () => {
    const ms = await navigator.mediaDevices.getUserMedia({ audio: true }); const mr = new MediaRecorder(ms); const chunks = [];
    mr.ondataavailable = (e) => chunks.push(e.data); mr.onstop = () => { ms.getTracks().forEach((t) => t.stop()); setBlob(new Blob(chunks, { type: mr.mimeType })); }; mr.start(); setRec(mr);
  };
  const save = async () => {
    const b64 = blob ? await new Promise((res) => { const r = new FileReader(); r.onload = () => res(String(r.result).split(",")[1]); r.readAsDataURL(blob); }) : "";
    await api.post("/life-stories", { title, transcript: tx, audio_b64: b64 }); setTitle(""); setBlob(null); setTx(""); speak("Your story is saved for your family.", lang); load();
  };
  const play = async (id) => new Audio(await api.blob(`/life-stories/${id}/audio`)).play();
  return <>
    <p>Record a memory in your own voice. Your family can keep it forever, if you choose to share stories with them.</p>
    <label>Title<input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="My village in the monsoon" /></label>
    {!rec || rec.state === "inactive" ? <button className="big mic" onClick={start}>⏺ Start recording</button> : <button className="big" onClick={() => rec.stop()}>⏹ Stop</button>}
    {blob && <audio controls src={URL.createObjectURL(blob)} />}
    <label>Or write it (optional)<textarea rows={3} value={tx} onChange={(e) => setTx(e.target.value)} /></label>
    <button className="big primary" disabled={!title || (!blob && !tx)} onClick={save}>Save story</button>
    {rows.map((r) => <div className="row" key={r.id}><span>{r.title}</span>{r.has_audio && <button onClick={() => play(r.id)}>▶ Play</button>}</div>)}
  </>;
}

function Messages({ lang }) {
  const [rows, setRows] = useState([]); useEffect(() => { api.get("/messages").then(setRows); }, []);
  const play = async (m) => { speak(m.speak, lang); if (m.has_file) { try { new Audio(await api.blob(`/messages/${m.id}/file`)).play(); } catch { /* not audio */ } } };
  return <>{!rows.length && <p className="note">No messages yet. Ask your grandchildren to send you a voice message.</p>}
    {rows.map((m) => <div className="card" key={m.id}><h3>{m.from} · {m.kind}</h3><p>{m.text}</p><button className="big" onClick={() => play(m)}>▶ Play</button></div>)}</>;
}
