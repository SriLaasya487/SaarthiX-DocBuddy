import { useState } from "react";
import { api } from "../api.js";
import { t as tr } from "../i18n.js";

export default function SosButton({ lang = "en-IN" }) {
  const [msg, setMsg] = useState("");
  const press = async () => {
    let location = "";
    try {
      const p = await new Promise((ok, no) => navigator.geolocation.getCurrentPosition(ok, no, { timeout: 4000 }));
      location = `${p.coords.latitude},${p.coords.longitude}`;
    } catch { /* location is optional */ }
    try {
      const r = await api.post("/sos", { location });
      setMsg(r.contacts_notified ? tr("Help is being told. {n} person(s) informed. You can also call 112.", lang, { n: r.contacts_notified })
        : tr("You have not chosen anyone for emergencies yet. Please call 112 now.", lang));
    } catch (e) { setMsg(tr("Could not send. Please call 112 now.", lang)); }
  };
  return (
    <>
      <button className="sos" onClick={press} aria-label="Emergency SOS">SOS</button>
      {msg && <div className="toast" role="alert">{msg} <a href="tel:112">{tr("Call 112", lang)}</a> <button onClick={() => setMsg("")}>{tr("OK", lang)}</button></div>}
    </>
  );
}
