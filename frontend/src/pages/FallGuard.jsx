import { useEffect, useRef, useState } from "react";
import { api } from "../api.js";
import { isYes, listen, speak } from "../voice.js";

// Detects a hard jolt followed by stillness using the phone accelerometer, then asks "Are you okay?".
// No answer in 60s -> server escalates to contacts the elder pre-approved. Real use: Android foreground service.
export default function FallGuard({ lang }) {
  const [alert, setAlert] = useState(null);
  const last = useRef(0);

  useEffect(() => {
    const onMotion = (e) => {
      const a = e.accelerationIncludingGravity; if (!a) return;
      const g = Math.sqrt((a.x || 0) ** 2 + (a.y || 0) ** 2 + (a.z || 0) ** 2) / 9.81;
      if (g > 3.2 && Date.now() - last.current > 30000) { last.current = Date.now(); trigger(); }
    };
    window.addEventListener("devicemotion", onMotion);
    return () => window.removeEventListener("devicemotion", onMotion);
  }, []);

  const trigger = async () => {
    const r = await api.post("/fall", {}).catch(() => null);
    if (!r) return;
    setAlert(r); speak("Are you okay? Say yes, or press I am fine.", lang);
    listen(lang).then((t) => isYes(t) && fine(r.alert_id)).catch(() => {});
  };
  const fine = async (id) => { await api.post(`/alerts/${id}/respond`, { allow: false }); setAlert(null); speak("Good. Stay safe.", lang); };

  if (!alert) return null;
  return (
    <div className="modal" role="alertdialog" aria-label="Are you okay?">
      <h2>Are you okay?</h2>
      <p>If you do not answer, your emergency contacts will be told.</p>
      <button className="big primary" onClick={() => fine(alert.alert_id)}>I am fine</button>
    </div>
  );
}
