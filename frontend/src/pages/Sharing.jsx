import { useEffect, useState } from "react";
import { api } from "../api.js";
import { t as tr } from "../translate.js";
import { canListen, listen, speak } from "../voice.js";

const ROLES = [["primary", "Main caregiver"], ["sibling", "Another family member"], ["doctor", "Doctor"], ["neighbour", "Trusted neighbour (reached first in an emergency)"],
  ["chw", "Health worker / nurse"], ["grandchild", "Grandchild"], ["guardian", "Legal guardian"], ["nominee", "Nominee (only for when I cannot decide)"]];

export default function Sharing({ lang }) {
  const [types, setTypes] = useState({});
  const [grants, setGrants] = useState([]);
  const [log, setLog] = useState([]);
  const [who, setWho] = useState({ phone: "", name: "", relation: "" });
  const [days, setDays] = useState("");
  const [role, setRole] = useState("primary");
  const [msg, setMsg] = useState("");

  const load = () => { api.get("/consents").then(setGrants); };
  useEffect(() => { api.get("/consents/types").then(setTypes); load(); }, []);
  const say = (m) => { setMsg(m); speak(m, lang); };

  const grant = async (data_type, scope = "view") => {
    await api.post("/consents", { grantee_phone: who.phone, grantee_name: who.name, data_type, scope, days: days ? +days : null, relation: who.relation });
    say("Okay. Shared."); load();
  };
  const revoke = async (id) => { await api.del(`/consents/${id}`); say("Stopped sharing."); load(); };
  const whoSaw = async () => { const r = await api.get("/consents/log"); setLog(r.sentences); speak(r.sentences.join(" "), lang); };

  // DB-082: "Stop sharing my mood with my son"
  const stopByVoice = async () => {
    speak("Tell me what to stop. For example: stop sharing my mood with my son.", lang);
    await new Promise((r) => setTimeout(r, 3500));
    const t = await listen(lang).catch(() => ""); if (!t) return say("I did not hear you.");
    const r = await api.post("/consents/revoke-by-voice", { text: t }); say(r.speak); load();
  };
  // DB-083: doctor sees a bundle for N days, then it ends by itself
  const doctor = async () => { const r = await api.post("/consents/share-with-doctor", { doctor_phone: who.phone, doctor_name: who.name, days: +days || 7 }); say(`Shared with ${r.shared_with} for ${r.days} days.`); load(); };
  // DB-053/062/080: add a helper with a role - the helper gets only that role's usual access, and only after YOU approve in "Please check"
  const invite = async () => { await api.post("/care-team/invite", { member_phone: who.phone, member_name: who.name, role, relation: who.relation, days: days ? +days : null }); say("I made a suggestion. Please open “Please check” to say yes."); };

  return (
    <section className="stack">
      <h2>{tr("Who can see what", lang)}</h2>
      <p>{tr("You decide. Nothing is shared unless you say Yes.", lang)}</p>
      {msg && <p className="note" role="status">{msg}</p>}

      <div className="card stack">
        <h3>{tr("Share with someone", lang)}</h3>
        <label>{tr("Their name", lang)}<input value={who.name} onChange={(e) => setWho({ ...who, name: e.target.value })} /></label>
        <label>{tr("Their mobile number", lang)}<input value={who.phone} onChange={(e) => setWho({ ...who, phone: e.target.value })} inputMode="tel" /></label>
        <label>What do you call them? (son, daughter, doctor…)<input value={who.relation} onChange={(e) => setWho({ ...who, relation: e.target.value })} /></label>
        <label>For how many days? (empty = until I stop)<input type="number" min="1" value={days} onChange={(e) => setDays(e.target.value)} /></label>
        {who.phone && <>
          <button className="big" onClick={doctor}>Share my visit summary with this doctor</button>
          <label>Or add as a helper with a role<select value={role} onChange={(e) => setRole(e.target.value)}>{ROLES.map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select></label>
          <button className="big" onClick={invite}>Suggest this role</button>
          <h3>Or choose item by item</h3>
          {Object.entries(types).map(([k, label]) => (
            <div className="row" key={k}><span>{label[0].toUpperCase() + label.slice(1)}</span>
              <span><button onClick={() => grant(k, k === "sos" ? "escalate" : k === "messages" || k === "video" || k === "services" ? "send" : "view")}>Yes</button>
                {k === "mood" && <button onClick={() => grant(k, "escalate")}>Can be alerted</button>}</span></div>
          ))}
        </>}
      </div>

      <h3>{tr("Currently shared", lang)}</h3>
      {grants.length === 0 && <p className="note">{tr("You are sharing nothing.", lang)}</p>}
      {grants.map((g) => (
        <div className="row" key={g.id}>
          <span>{g.grantee}{g.relation ? ` (${g.relation})` : ""}: {types[g.data_type] || g.data_type}{g.scope !== "view" ? ` · ${g.scope}` : ""}{g.expires_at ? " · temporary" : ""}</span>
          <button className="stop" onClick={() => revoke(g.id)}>{tr("Stop", lang)}</button>
        </div>
      ))}
      {canListen() && <button className="big mic" onClick={stopByVoice}>{tr("🎤 Stop sharing by voice", lang)}</button>}
      <button className="big" onClick={whoSaw}>{tr("🔊 Who saw my information?", lang)}</button>
      {log.map((l, i) => <p className="note" key={i}>{l}</p>)}
    </section>
  );
}
