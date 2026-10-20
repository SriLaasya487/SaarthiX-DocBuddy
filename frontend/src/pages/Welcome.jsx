import { useEffect, useState } from "react";
import { t as tr } from "../translate.js";
import { speak } from "../voice.js";

// Three short screens shown once to a new senior.
const SLIDES = [
  { icon: "🎤", title: "Just speak", body: "Press the microphone and say what you need. No typing needed." },
  { icon: "🔐", title: "You decide who sees what", body: "Nothing is shared with your family or doctor unless you say Yes. You can stop at any time." },
  { icon: "🛟", title: "The red SOS button", body: "If you ever need help, press the red SOS button. Your family will be told." },
];

export default function Welcome({ lang, onDone }) {
  const [i, setI] = useState(0);
  const s = SLIDES[i], last = i === SLIDES.length - 1;
  useEffect(() => { speak(tr(s.title, lang) + ". " + tr(s.body, lang), lang); }, [i]);
  return (
    <div className="modal-overlay" role="dialog" aria-label="Welcome">
      <div className="modal-card" style={{ textAlign: "center", alignItems: "center" }}>
        <div style={{ fontSize: "4.5rem", lineHeight: 1 }} aria-hidden>{s.icon}</div>
        <h2 style={{ margin: 0, color: "var(--rose-primary)" }}>{tr(s.title, lang)}</h2>
        <p style={{ margin: 0, fontSize: "1.1rem" }}>{tr(s.body, lang)}</p>
        <div style={{ display: "flex", gap: ".5rem" }} aria-hidden>
          {SLIDES.map((_, k) => <span key={k} style={{ width: ".8rem", height: ".8rem", borderRadius: "50%", background: k === i ? "var(--rose-primary)" : "var(--line)" }} />)}
        </div>
        <button className="big-action rose-filled" onClick={() => (last ? onDone() : setI(i + 1))}>{last ? tr("Let's begin", lang) : tr("Next", lang)}</button>
        {!last && <button style={{ background: "none", border: 0, color: "var(--ink-muted)", textDecoration: "underline", cursor: "pointer", font: "inherit" }} onClick={onDone}>{tr("Skip", lang)}</button>}
      </div>
    </div>
  );
}
