import { useEffect, useState } from "react";
import { t as tr } from "../i18n.js";
import { speak } from "../voice.js";

// Three short screens shown once to a new senior.
const SLIDES = [
  { icon: "🎤", title: "Just speak", body: "Press the microphone and say what you need. No typing needed." },
  { icon: "🔐", title: "You decide who sees what", body: "Nothing is shared with your family or doctor unless you say Yes. You can stop at any time." },
  { icon: "🛟", title: "The red SOS button", body: "If you ever need help, press the red SOS button. Your family will be told." },
];

export default function Welcome({ lang, onDone }) {
  const [i, setI] = useState(0);
  const s = SLIDES[i];
  useEffect(() => { speak(tr(s.title, lang) + ". " + tr(s.body, lang), lang); }, [i]);
  const last = i === SLIDES.length - 1;
  return (
    <div className="tour" role="dialog" aria-label="Welcome">
      <div className="em" aria-hidden>{s.icon}</div>
      <h1>{tr(s.title, lang)}</h1>
      <p>{tr(s.body, lang)}</p>
      <div className="dots" aria-hidden>{SLIDES.map((_, k) => <span key={k} className={k === i ? "on" : ""} />)}</div>
      <button className="big primary" onClick={() => (last ? onDone() : setI(i + 1))}>{last ? tr("Let's begin", lang) : tr("Next", lang)}</button>
      {!last && <button className="skip" onClick={onDone}>{tr("Skip", lang)}</button>}
    </div>
  );
}
