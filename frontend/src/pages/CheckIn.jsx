import { useEffect, useState } from "react";
import { api } from "../api.js";
import { t as tr } from "../i18n.js";
import { canListen, isNo, isYes, listen, speak } from "../voice.js";

// Five simple questions, answered by voice or large buttons.
const QUESTIONS = [
  { key: "mood", text: "How are you feeling today?", options: [["good", "Good 😊"], ["okay", "Okay 😐"], ["low", "Not well 😔"]] },
  { key: "pain", text: "Do you have any pain?", options: [["none", "No pain"], ["mild", "A little"], ["strong", "Strong pain"]] },
  { key: "took_medicines", text: "Have you taken your medicines?", options: [[true, "Yes"], [false, "No"]] },
  { key: "needs_help", text: "Do you need any help today?", options: [[false, "No"], [true, "Yes, I need help"]] },
  { key: "doctor_visit_soon", text: "Do you have a doctor visit coming up?", options: [[false, "No"], [true, "Yes"]] },
];
const VOICE_MAP = {
  mood: (t) => (/good|fine|accha|bagunna|நன்று/i.test(t) ? "good" : /bad|low|not well|bura|dukhi/i.test(t) ? "low" : "okay"),
  pain: (t) => (/strong|a lot|bahut|too much/i.test(t) ? "strong" : isNo(t) ? "none" : "mild"),
};

export default function CheckIn({ lang, onDone }) {
  const [i, setI] = useState(0);
  const [ans, setAns] = useState({});
  const [result, setResult] = useState(null);
  const q = QUESTIONS[i];

  useEffect(() => { if (q) speak(q.text, lang); }, [i]);

  const answer = async (v) => {
    const next = { ...ans, [q.key]: v };
    setAns(next);
    if (i < QUESTIONS.length - 1) return setI(i + 1);
    const r = await api.post("/checkin", next);
    setResult(r);
    speak(r.ask_to_inform_family_alert_id || r.ask_low_mood_alert_id ? "Shall I tell someone you trust?" : "Thank you. Have a lovely day.", lang);
  };

  const byVoice = async () => {
    try {
      const t = await listen(lang);
      if (VOICE_MAP[q.key]) answer(VOICE_MAP[q.key](t));
      else if (isYes(t)) answer(true); else if (isNo(t)) answer(false);
    } catch { speak("Sorry, please use the buttons.", lang); }
  };

  if (result) {
    const id = result.ask_to_inform_family_alert_id || result.ask_low_mood_alert_id;
    return (
      <section className="stack">
        <h2>{tr("Thank you!", lang)}</h2>
        {result.pattern_note && <p className="note">{result.pattern_note}</p>}
        {id ? (
          <>
            <p>{result.ask_low_mood_alert_id && !result.ask_to_inform_family_alert_id ? tr("You have felt low for some weeks. Shall I let someone you trust know, so they can call you?", lang) : tr("Shall I tell your family that you need help?", lang)}</p>
            <button className="big primary" onClick={async () => { await api.post(`/alerts/${id}/respond`, { allow: true }); onDone(); }}>{tr("Yes, tell them", lang)}</button>
            <button className="big" onClick={async () => { await api.post(`/alerts/${id}/respond`, { allow: false }); onDone(); }}>{tr("No, don't tell", lang)}</button>
          </>
        ) : <button className="big primary" onClick={onDone}>{tr("Done", lang)}</button>}
      </section>
    );
  }
  return (
    <section className="stack">
      <p className="step">{tr("Question {i} of {n}", lang, { i: i + 1, n: QUESTIONS.length })}</p>
      <h2>{tr(q.text, lang)}</h2>
      {q.options.map(([v, label]) => <button key={String(v)} className="big" onClick={() => answer(v)}>{tr(label, lang)}</button>)}
      {canListen() && <button className="big mic" onClick={byVoice}>{tr("🎤 Answer by voice", lang)}</button>}
    </section>
  );
}
