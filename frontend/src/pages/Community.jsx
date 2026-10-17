import { useEffect, useState } from "react";
import { api } from "../api.js";
import { canListen, dictate, speak } from "../voice.js";

// DB-051: moderated rooms. Only your first name is shown; links, money talk and phone numbers are held for a moderator.
export default function Community({ lang }) {
  const [rooms, setRooms] = useState([]); const [room, setRoom] = useState(null); const [posts, setPosts] = useState([]); const [t, setT] = useState(""); const [msg, setMsg] = useState(""); const [joined, setJoined] = useState(false);
  useEffect(() => { api.get("/community/rooms").then(setRooms); api.get("/settings").then((s) => setJoined(s.community)); }, []);
  const open = async (r) => { setRoom(r); setPosts(await api.get(`/community/rooms/${r.id}/posts`)); };
  const post = async (text = t) => { const r = await api.post(`/community/rooms/${room.id}/posts`, { text }); setMsg(r.posted ? "Posted." : r.note); setT(""); open(room); };
  if (!joined) return <section className="stack"><h2>Friends</h2><p>Meet other seniors in friendly rooms: satsang, bhajans, walking, stories, chess. Your first name only is shown. Joining is your choice.</p>
    <button className="big primary" onClick={async () => { await api.post("/community/join"); setJoined(true); speak("Welcome.", lang); }}>Join the community</button></section>;
  if (!room) return <section className="stack"><h2>Friends</h2>{rooms.map((r) => <button className="big" key={r.id} onClick={() => open(r)}>{r.name}</button>)}</section>;
  return <section className="stack"><button className="back" onClick={() => setRoom(null)}>← Rooms</button><h2>{room.name}</h2>
    {posts.map((p) => <div className="card" key={p.id}><p><b>{p.name}:</b> {p.text}</p><button onClick={() => speak(p.text, lang)}>🔊</button> <button className="stop" onClick={async () => { await api.post(`/community/posts/${p.id}/report`); open(room); }}>Report</button></div>)}
    {msg && <p className="note">{msg}</p>}
    <input value={t} onChange={(e) => setT(e.target.value)} placeholder="Say something kind" />{canListen() && <button className="big mic" onClick={async () => { const x = await dictate(lang); if (x) post(x); }}>🎤 Speak</button>}
    <button className="big primary" disabled={!t.trim()} onClick={() => post()}>Post</button></section>;
}
