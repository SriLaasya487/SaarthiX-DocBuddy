import { useEffect, useState } from "react";
import { api } from "../api.js";
import { applySettings } from "../a11y.js";
import { bleSupported } from "../bluetooth.js";
import { LANGUAGES, SUPPORTED, canListen, dictate, speak } from "../voice.js";

const DIALECTS = ["", "te-IN:Telangana", "hi-IN:Bhojpuri", "mr-IN:Vidarbha", "hi-IN:Haryanvi"];

export default function Settings({ lang, user, onUser }) {
  const [s, setS] = useState(null); const [msg, setMsg] = useState(""); const [plans, setPlans] = useState(null); const [tier, setTier] = useState(null); const [dev, setDev] = useState(null); const [devs, setDevs] = useState([]);
  const [fb, setFb] = useState({ heard: "", meant: "", dialect: "" }); const [rec, setRec] = useState(null);
  useEffect(() => { api.get("/settings").then(setS); api.get("/pricing").then(setPlans); api.get(`/billing/${user.id}`).then(setTier); api.get("/devices").then(setDevs); }, []);
  if (!s) return null;
  const save = async (patch, say) => { const r = await api.put("/settings", patch); setS(r); applySettings(r); if (say) { setMsg(say); speak(say, lang); } };
  const Toggle = ({ k, label, say }) => <label className="chk"><input type="checkbox" checked={!!s[k]} onChange={(e) => save({ [k]: e.target.checked }, say)} />{label}</label>;
  const here = () => navigator.geolocation.getCurrentPosition((p) => save({ lat: +p.coords.latitude.toFixed(3), lng: +p.coords.longitude.toFixed(3) }, "Saved your area."), () => setMsg("Could not get location."));
  const exp = async () => { const d = await api.get("/me/export"); const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob([JSON.stringify(d, null, 2)], { type: "application/json" })); a.download = "my-docbuddy-data.json"; a.click(); };
  const del = async () => { if (window.confirm("This deletes your account and ALL your information. It cannot be undone. Continue?")) { await api.del("/me?confirm=true"); localStorage.clear(); location.reload(); } };

  return (
    <section className="stack">
      <h2>Settings</h2>{msg && <p className="note" role="status">{msg}</p>}

      <div className="card stack"><h3>Seeing & hearing</h3>
        <label>Text size ({Math.round(s.font_scale * 100)}%)<input type="range" min="1" max="2" step="0.1" value={s.font_scale} onChange={(e) => save({ font_scale: +e.target.value })} /></label>
        <Toggle k="high_contrast" label="High contrast colours" /><Toggle k="captions" label="Show words on screen when DocBuddy speaks" />
        <Toggle k="vibrate_flash" label="Vibrate and flash the screen for important alerts" />
        <label>Speaking speed<input type="range" min="0.5" max="1.4" step="0.1" value={s.speech_rate} onChange={(e) => save({ speech_rate: +e.target.value })} /></label>
        <label>Simple mode for slow phones<select value={s.lite_mode} onChange={(e) => save({ lite_mode: e.target.value })}><option value="auto">Automatic</option><option value="on">Always on</option><option value="off">Off</option></select></label></div>

      <div className="card stack"><h3>Language & how I speak</h3>
        <label>Language<select value={user.language} onChange={async (e) => { await api.patch("/me", { language: e.target.value }); onUser({ ...user, language: e.target.value }); }}>{LANGUAGES.filter((l) => SUPPORTED.includes(l.code)).map((l) => <option key={l.code} value={l.code}>{l.label}</option>)}</select></label>
        <label>My way of speaking (dialect)<select value={s.dialect} onChange={(e) => save({ dialect: e.target.value })}>{DIALECTS.map((d) => <option key={d} value={d}>{d || "standard"}</option>)}</select></label>
        <p className="note">If DocBuddy mis-hears you, teach it:</p>
        <label>What I said<input value={fb.heard} onChange={(e) => setFb({ ...fb, heard: e.target.value })} /></label>
        <label>What I meant<input value={fb.meant} onChange={(e) => setFb({ ...fb, meant: e.target.value })} /></label>
        <button className="big" disabled={!fb.heard || !fb.meant} onClick={async () => { await api.post("/dialect/feedback", { ...fb, dialect: s.dialect }); setFb({ heard: "", meant: "", dialect: "" }); setMsg("Thank you, this helps."); }}>Send</button></div>

      <details className="more"><summary>More settings</summary>
      <div className="card stack"><h3>Reminders & nudges</h3>
        {[["hydration", "Drink water"], ["meal", "Meals"], ["walk", "A gentle walk"]].map(([k, l]) => <label className="chk" key={k}><input type="checkbox" checked={!!s.nudges?.[k]?.on} onChange={(e) => save({ nudges: { ...s.nudges, [k]: { ...(s.nudges?.[k] || {}), on: e.target.checked } } })} />{l}</label>)}
        <Toggle k="activity_tracking" label="Let DocBuddy note my sleep and steps (from my phone or watch)" />
        <label>Pharmacy WhatsApp number<input value={s.pharmacy_phone} inputMode="tel" onChange={(e) => setS({ ...s, pharmacy_phone: e.target.value })} onBlur={() => save({ pharmacy_phone: s.pharmacy_phone })} /></label>
        <label>Family doctor's mobile<input value={s.family_doctor_phone} inputMode="tel" onChange={(e) => setS({ ...s, family_doctor_phone: e.target.value })} onBlur={() => save({ family_doctor_phone: s.family_doctor_phone })} /></label>
        <label>Faith (for prayers)<select value={s.faith} onChange={(e) => save({ faith: e.target.value })}>{["", "hindu", "sikh", "muslim", "christian", "buddhist", "jain"].map((f) => <option key={f} value={f}>{f || "not set"}</option>)}</select></label>
        <button className="big" onClick={here}>📍 Save my area (for weather, prayer times)</button></div>

      <div className="card stack"><h3>Phone calls (no smartphone needed)</h3><p>DocBuddy can phone you for the daily check-in and read your medicines. You answer by pressing numbers. Press 9 any time for an emergency.</p>
        <label>How should DocBuddy reach me?<select value={user.channel} onChange={async (e) => { await api.patch("/me", { channel: e.target.value }); onUser({ ...user, channel: e.target.value }); }}><option value="app">App</option><option value="ivr">Phone call</option><option value="whatsapp">WhatsApp</option><option value="sms">SMS</option></select></label></div>

      <div className="card stack"><h3>Devices</h3>
        {devs.map((d) => <div className="row" key={d.id}><span>{d.kind}</span><span className="note">{d.last_sync ? "synced" : "not synced yet"}</span></div>)}
        {bleSupported() ? <p className="note">Bluetooth BP / sugar / oxygen: use the buttons on the Readings page.</p> : <p className="note">This browser cannot use Bluetooth. Use Chrome on Android.</p>}
        <div className="grid2">{["watch", "speaker"].map((k) => <button className="big" key={k} onClick={async () => { try { setDev(await api.post("/devices", { kind: k })); } catch (e) { setMsg(e.message); } }}>Connect {k}</button>)}</div>
        {dev && <p className="note">Put this code in the {dev.token ? "device" : ""} app as X-Device-Token: <b style={{ wordBreak: "break-all" }}>{dev.token}</b></p>}</div>

      <div className="card stack"><h3>Community & research</h3>
        <Toggle k="community" label="I want to meet friends in the Friends rooms" />
        <Toggle k="aggregate_opt_in" label="Include my anonymous numbers in area health statistics (never my name)" />
        {s.aggregate_opt_in && <label>My area (district / city)<input value={s.region} onChange={(e) => setS({ ...s, region: e.target.value })} onBlur={() => save({ region: s.region })} /></label>}</div>

      {plans && <div className="card stack"><h3>My plan: {tier?.tier || "free"}</h3><p className="note">Safety is free forever: emergency button, fall detection, medicine reminders, daily check-in, emergency card and your privacy controls.</p>
        {plans.tiers.map((p) => <div key={p.id} className="row"><span><b>{p.id}</b> · ₹{p.price_per_month}/month<br /><span className="note">{p.includes.join(" · ")}</span></span>
          {p.id !== tier?.tier && <button onClick={async () => { try { await api.post("/billing/subscribe", { elder_id: user.id, tier: p.id }); setTier({ ...tier, tier: p.id }); } catch (e) { setMsg(e.message); } }}>Choose</button>}</div>)}
        <p className="note">{plans.note}</p></div>}

      </details>

      <div className="card stack"><h3>My data</h3><p>It is yours. Download everything, or delete it all.</p>
        <button className="big" onClick={exp}>⬇ Download my data</button><button className="big" onClick={async () => { const r = await api.get("/me/consent-records"); setMsg(`${r.length} sharing decisions on record. They are included in the download.`); }}>My sharing record</button>
        <button className="big" style={{ borderColor: "var(--sos)", color: "var(--sos)" }} onClick={del}>Delete my account and data</button></div>
    </section>
  );
}
