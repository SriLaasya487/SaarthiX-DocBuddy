import { lazy, Suspense, useCallback, useEffect, useState } from "react";
import { api, syncNow, isDemo } from "../api.js";
import { applySettings, attention } from "../a11y.js";
import { pendingCount, scheduleDoseAlarms } from "../offline.js";
import { t as tr } from "../i18n.js";
import { canListen, hearAgain, listen, loadLexicon, slowDown, speak, voiceNav } from "../voice.js";
import CheckIn from "./CheckIn.jsx";
import Welcome from "./Welcome.jsx";
import Medicines from "./Medicines.jsx";
import Doctor from "./Doctor.jsx";
import Sharing from "./Sharing.jsx";
import Health from "./Health.jsx";
import Pending from "./Pending.jsx";
import SosButton from "./SosButton.jsx";
import FallGuard from "./FallGuard.jsx";
// heavier pages load only when opened (smaller first download for slow phones)
const Records = lazy(() => import("./Records.jsx"));
const Companion = lazy(() => import("./Companion.jsx"));
const SafetyHub = lazy(() => import("./SafetyHub.jsx"));
const Assistant = lazy(() => import("./Assistant.jsx"));
const Daily = lazy(() => import("./Daily.jsx"));
const Community = lazy(() => import("./Community.jsx"));
const Settings = lazy(() => import("./Settings.jsx"));

const TILES = [
  { id: "checkin", label: "Daily check-in", icon: "😊" }, { id: "meds", label: "My medicines", icon: "💊" }, { id: "health", label: "BP, sugar & visits", icon: "❤️" },
  { id: "records", label: "My records", icon: "📁" }, { id: "doctor", label: "Which doctor?", icon: "🩺" }, { id: "companion", label: "Companion", icon: "🌼" },
  { id: "assistant", label: "Ask AarogyaSaathi", icon: "💬" }, { id: "safety", label: "Staying safe", icon: "🛡️" }, { id: "daily", label: "Learn & benefits", icon: "📖" },
  { id: "community", label: "Friends", icon: "👥" }, { id: "sharing", label: "Who can see what", icon: "🔐" }, { id: "settings", label: "Settings", icon: "⚙️" },
];

export default function ElderApp({ user: u0, onLogout }) {
  const [user, setUser] = useState(u0);
  const [view, setView] = useState("home");
  const [home, setHome] = useState(null);
  const [caption, setCaption] = useState("");
  const [call, setCall] = useState(null);
  const [alarm, setAlarm] = useState(null);
  const [fine, setFine] = useState(null);
  const [more, setMore] = useState(false);
  const [tour, setTour] = useState(!localStorage.getItem("db_tour"));
  const lang = user.language;

  useEffect(() => { applySettings(u0.settings || {}); loadLexicon(api.get); syncNow(); }, []);
  useEffect(() => { const f = (e) => { setCaption(e.detail); clearTimeout(window.__cap); window.__cap = setTimeout(() => setCaption(""), 9000); }; window.addEventListener("db-caption", f); return () => window.removeEventListener("db-caption", f); }, []);

  // one small request feeds the home screen (and is cached for offline use)
  const refresh = useCallback(() => api.get("/lite/home").then((h) => { setHome(h); scheduleDoseAlarms(h.medicines, (d) => { attention(); speak(`Time for ${d.name}.`, lang); setAlarm(d); }); }).catch(() => {}), [lang]);
  useEffect(() => { refresh(); const t = setInterval(refresh, 60000); return () => clearInterval(t); }, [view, refresh]);
  useEffect(() => { const t = setInterval(() => api.get("/video/incoming").then((v) => { if (v[0]) { setCall(v[0]); attention(); speak(`${v[0].from} is calling you on video.`, lang); } }).catch(() => {}), 15000); return () => clearInterval(t); }, [lang]);

  const due = home?.due || [];
  useEffect(() => {
    if (view !== "home" || !home) return;
    const nonEn = !lang.startsWith("en");
    const parts = [tr("Namaste {name}.", lang, { name: user.name }), due.length ? tr("You have {n} medicine(s) to take.", lang, { n: due.length }) : tr("Everything is on track.", lang), ...(nonEn ? [] : [...(home.appointments || []).map((a) => a.speak), ...(home.reminders || []).map((r) => r.say), ...(home.nudges || []).map((n) => n.say)])];
    speak(parts.join(" "), lang); if (due.length || home.appointments?.length) attention();
  }, [view, !!home, due.length]);

  const go = (v) => setView(v);
  const bump = (d) => { let s = {}; try { s = JSON.parse(localStorage.getItem("db_a11y")) || {}; } catch { /* none */ } s.font_scale = Math.min(2, Math.max(1, +((s.font_scale || 1) + d).toFixed(1))); applySettings(s); api.put("/settings", { font_scale: s.font_scale }).catch(() => {}); };
  const Back = () => <button className="back" onClick={() => go("home")}>← Home</button>;
  const sayFine = async () => { const d = await api.post("/imfine"); setFine(d); speak(d.speak, lang); };

  // DB-001: say where you want to go
  const voiceGo = async () => { speak("Where would you like to go?", lang); await new Promise((r) => setTimeout(r, 1800)); const t = await listen(lang).catch(() => ""); const v = voiceNav(t); if (v) go(v === "home" ? "home" : v); else speak("I did not understand. Please tap a button.", lang); };

  const badge = (id) => (id === "meds" && due.length) || (id === "companion" && home?.unread_messages) || (id === "sharing" && home?.pending) ? <span className="badge">{id === "meds" ? due.length : id === "companion" ? home.unread_messages : home.pending}</span> : null;
  const queued = pendingCount();
  const MAIN = ["checkin", "meds", "health", "sharing", "assistant", "safety"];
  const shown = more ? TILES : MAIN.map((id) => TILES.find((x) => x.id === id));

  return (
    <div className="shell">
      {tour && <Welcome lang={lang} onDone={() => { localStorage.setItem("db_tour", "1"); setTour(false); }} />}
      <header className="bar">
        <strong className="logo">🪔 AarogyaSaathi</strong>
        <span className="tools">
          <button aria-label="Smaller text" onClick={() => bump(-0.1)}>A−</button>
          <button aria-label="Bigger text" onClick={() => bump(0.1)}><b>A+</b></button>
          <button onClick={onLogout}>{tr("Sign out", lang)}</button>
        </span>
      </header>
      {queued > 0 && <p className="note" style={{ padding: "0 1rem" }}>{queued} item(s) saved on this phone, waiting for the network.</p>}
      {home?.disaster && <p className="warn" style={{ padding: "0 1rem" }}><b>Extra safety mode is on.</b> <button className="back" onClick={() => go("safety")}>See what to do</button></p>}

      <FallGuard lang={lang} />

      {call && <div className="modal" role="alertdialog"><p>📹 {call.from} is calling you</p>
        <button className="big ok" onClick={async () => { const r = await api.post(`/video/${call.id}`, { accept: true }); window.open(r.room_url, "_blank"); setCall(null); }}>Answer</button>
        <button className="big" onClick={async () => { await api.post(`/video/${call.id}`, { accept: false }); setCall(null); }}>Not now</button></div>}
      {alarm && <div className="modal" role="alertdialog"><p>💊 Time for {alarm.name} ({alarm.tablets})</p><button className="big ok" onClick={() => { setAlarm(null); go("meds"); }}>Open medicines</button><button className="big" onClick={() => setAlarm(null)}>Later</button></div>}

      <main className="page">
        {view === "home" && (
          <>
            <h1 className="greet">{tr("Namaste", lang)}, {user.name || "friend"} 🙏</h1>
            <p className="today">{new Date().toLocaleDateString("en-IN", { weekday: "long", day: "numeric", month: "long" })}</p>
            <div className="chips">
              <button onClick={hearAgain}>🔊 {tr("Hear again", lang)}</button>
              <button onClick={slowDown}>🐢 {tr("Slow down", lang)}</button>
              {canListen() && <button onClick={voiceGo}>🎤 {tr("Go to…", lang)}</button>}
              {isDemo && <button onClick={() => window.dispatchEvent(new Event("db-sim-fall"))}>⚠ Simulate fall</button>}
            </div>
            {home && !(home.medicines || []).length && <button className="due" onClick={() => go("meds")}>➕ {tr("Add your first medicine", lang)} →</button>}
            {due.length > 0 && <button className="due" onClick={() => go("meds")}>Medicine time: {due[0].name}{due.length > 1 ? ` and ${due.length - 1} more` : ""} →</button>}
            {(home?.appointments || []).map((a) => <button className="due" key={a.id} onClick={() => go("health")}>{a.speak}</button>)}
            {(home?.reminders || []).map((r, i) => <div className="card good" key={i}><p>🎉 {r.say}</p></div>)}
            {(home?.nudges || []).map((n, i) => <div className="card" key={i}><p>{n.say}</p></div>)}
            <div className="tiles small">
              {shown.map((t) => <button key={t.id} className="tile" onClick={() => go(t.id)}><span className="ico" aria-hidden>{t.icon}</span>{tr(t.label, lang)}{badge(t.id)}</button>)}
            </div>
            <button className="big" style={{ marginTop: "1rem" }} onClick={() => setMore(!more)}>{more ? tr("Fewer", lang) : tr("More", lang)}</button>
            {home?.pending > 0 && <button className="big primary" style={{ marginTop: "1rem" }} onClick={() => go("pending")}>Please check {home.pending} thing(s)</button>}
            <button className="big ok" style={{ marginTop: "1rem" }} onClick={sayFine}>👍 {tr("Tell my family I am fine", lang)}</button>
            {fine && fine.draft && <div className="card stack"><p>{fine.draft}</p><button className="big ok" onClick={async () => { const r = await api.post("/imfine?approve=true"); setFine(null); speak(r.speak, lang); }}>Yes, send it</button><button className="big" onClick={() => setFine(null)}>No</button></div>}
          </>
        )}
        <Suspense fallback={<p className="note">Loading…</p>}>
          {view === "checkin" && <><Back /><CheckIn lang={lang} onDone={() => go("home")} /></>}
          {view === "meds" && <><Back /><Medicines lang={lang} onPending={refresh} /></>}
          {view === "doctor" && <><Back /><Doctor lang={lang} /></>}
          {view === "health" && <><Back /><Health lang={lang} /></>}
          {view === "records" && <><Back /><Records lang={lang} onPending={refresh} /></>}
          {view === "companion" && <><Back /><Companion lang={lang} /></>}
          {view === "assistant" && <><Back /><Assistant lang={lang} onNavigate={(r) => go(r === "sharing" ? "sharing" : r)} /></>}
          {view === "safety" && <><Back /><SafetyHub lang={lang} /></>}
          {view === "daily" && <><Back /><Daily lang={lang} /></>}
          {view === "community" && <><Back /><Community lang={lang} /></>}
          {view === "sharing" && <><Back /><Sharing lang={lang} /></>}
          {view === "pending" && <><Back /><Pending lang={lang} onChange={refresh} /></>}
          {view === "settings" && <><Back /><Settings lang={lang} user={user} onUser={setUser} /></>}
        </Suspense>
      </main>

      {caption && <div className="captions" role="status" aria-live="polite">{caption}</div>}
      {isDemo && <p className="foot">Sample data for preview. Nothing here is stored.</p>}
      <SosButton lang={lang} />
    </div>
  );
}
