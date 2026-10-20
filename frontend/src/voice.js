// Voice helpers on top of the browser Web Speech API.
// Fixes: picks a real installed voice, never reads English in a Hindi/Telugu voice, waits for the first tap
// (browsers block sound before that), speaks long text in pieces, and listens only after speech has ended.
import { translate } from "./translate.js";

const W = typeof window !== "undefined" ? window : {};
const synth = W.speechSynthesis;

export const LANGUAGES = [
  { code: "en-IN", label: "English", native: "English", english: "English" },
  { code: "hi-IN", label: "हिन्दी", native: "हिन्दी", english: "Hindi" },
  { code: "te-IN", label: "తెలుగు", native: "తెలుగు", english: "Telugu" },
  { code: "ta-IN", label: "தமிழ்", native: "தமிழ்", english: "Tamil" },
  { code: "kn-IN", label: "ಕನ್ನಡ", native: "ಕನ್ನಡ", english: "Kannada" },
  { code: "mr-IN", label: "मराठी", native: "मराठी", english: "Marathi" },
  { code: "gu-IN", label: "ગુજરાતી", native: "ગુજરાતી", english: "Gujarati" },
  { code: "bn-IN", label: "বাংলা", native: "বাংলা", english: "Bengali" },
];
// Languages whose screens are fully translated (see i18n.js). Add a code here once its text is translated.
export const SUPPORTED = ["en-IN", "hi-IN", "te-IN", "ta-IN", "kn-IN", "mr-IN", "gu-IN", "bn-IN"];

let lastText = "", lastLang = "en-IN", rate = 0.9, pending = null;
export const setRate = (r) => { rate = r; };
export const getRate = () => rate;

// ---------- voices ----------
let voices = [];
const loadVoices = () => { voices = synth ? synth.getVoices() || [] : []; };
if (synth) { loadVoices(); synth.addEventListener?.("voiceschanged", loadVoices); }
const norm = (l) => String(l || "").toLowerCase().replace("_", "-");
function pickVoice(lang) {
  const l = norm(lang), p = l.slice(0, 2);
  const exact = voices.filter((v) => norm(v.lang) === l);
  const pool = exact.length ? exact : voices.filter((v) => norm(v.lang).startsWith(p));
  return pool.find((v) => /google|natural|online/i.test(v.name)) || pool[0] || null;
}
// true when we cannot tell yet (voices still loading) or a matching voice exists
export const hasVoice = (lang) => !voices.length || !!pickVoice(lang);
const caption = (text) => W.dispatchEvent?.(new CustomEvent("db-caption", { detail: text }));
const warned = {};
const isIndic = (s) => /[^\u0000-\u024F]/.test(s);

// ---------- speaking ----------
// Natural voices from the server (Google / Bhashini) when VITE_API_URL is set. Falls back to the phone's own voice.
const BASE = import.meta.env?.VITE_API_URL || "";
const CLOUD = !!BASE && import.meta.env?.VITE_TTS !== "off";
export const cloudVoiceOn = () => CLOUD;
const audioCache = new Map();
let audioEl = null, token = 0;
const stopAudio = () => { token++; try { audioEl?.pause(); } catch { /* none */ } };

async function fetchAudio(text, lang) {
  const key = `${lang}|${rate.toFixed(1)}|${text}`;
  if (audioCache.has(key)) return audioCache.get(key);
  const ctl = new AbortController(), timer = setTimeout(() => ctl.abort(), 10000);   // a sleeping server may be slow: fall back
  try {
    const r = await fetch(BASE + "/tts", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text, lang, rate }), signal: ctl.signal });
    if (!r.ok) throw new Error("tts " + r.status);
    const url = URL.createObjectURL(await r.blob());
    audioCache.set(key, url);
    return url;
  } finally { clearTimeout(timer); }
}
const groups = (text) => {
  const parts = text.match(/[^.!?।\n]+[.!?।]?/g) || [text], out = []; let cur = "";
  for (const p of parts) { if ((cur + p).length > 280 && cur) { out.push(cur.trim()); cur = p; } else cur += p; }
  if (cur.trim()) out.push(cur.trim());
  return out;
};
const playUrl = (url) => new Promise((resolve, reject) => {
  audioEl = audioEl || new Audio();
  audioEl.onended = resolve; audioEl.onerror = () => reject(new Error("audio"));
  audioEl.src = url; audioEl.play().catch(reject);
});
async function sayCloud(out, lang) {
  synth?.cancel(); stopAudio();
  const mine = token, parts = groups(out);
  const urls = parts.map((p) => fetchAudio(p, lang));
  urls.forEach((u) => u.catch(() => {}));
  for (let i = 0; i < parts.length; i++) {
    let url;
    try { url = await urls[i]; } catch (e) { if (i === 0) throw e; return; }
    if (mine !== token) return;
    await playUrl(url);
    if (mine !== token) return;
  }
}

function say(out, lang) {
  stopAudio(); synth.cancel();
  const chunks = out.match(/[^.!?।\n]+[.!?।]?/g) || [out];
  return new Promise((resolve) => {
    let i = 0, done = false;
    const finish = () => { if (!done) { done = true; resolve(); } };
    setTimeout(finish, 4000 + out.length * 120);
    const next = () => {
      if (i >= chunks.length) return finish();
      const c = chunks[i++].trim(); if (!c) return next();
      const u = new SpeechSynthesisUtterance(c);
      u.lang = lang; u.rate = rate;
      const v = pickVoice(lang); if (v) u.voice = v;
      u.onend = next;
      u.onerror = (e) => { if (e.error === "not-allowed") pending = { out, lang }; finish(); };
      synth.speak(u);
    };
    setTimeout(next, 60);   // Chrome drops speech started right after cancel()
  });
}
// cloud voice for non-English when available, otherwise the phone's voice
function play(out, lang, orig = out) {
  if (CLOUD && !lang.startsWith("en")) {
    return sayCloud(out, lang).catch((e) => {
      if (e?.name === "NotAllowedError") { pending = { out, lang }; return; }
      return deviceSpeak(orig, out, lang);
    });
  }
  return deviceSpeak(orig, out, lang);
}
function deviceSpeak(orig, out, lg) {
  if (!synth) return Promise.resolve();
  // This phone has no voice for the language: read the English original instead (or show text only)
  if (!lg.startsWith("en") && !hasVoice(lg)) {
    if (!warned[lg]) { warned[lg] = 1; caption(`No ${(LANGUAGES.find((x) => x.code === lg) || {}).english || lg} voice on this device. Showing text only. Try Chrome on Android.`); }
    if (!isIndic(orig)) { out = orig; lg = "en-IN"; } else { caption(out); return Promise.resolve(); }
  }
  return say(out, lg);
}

export function speak(text, lang = lastLang) {
  if (!text) return Promise.resolve();
  const orig = String(text);
  let out = orig, lg = lang;
  out = out.replace(/DocBuddy/g, "AarogyaSaathi");
  if (!isIndic(out)) { const tr = !lg.startsWith("en") ? translate(out, lg) : null; if (tr) out = tr; else lg = "en-IN"; }
  lastText = out; lastLang = lg;
  caption(out);
  const active = !W.navigator?.userActivation || W.navigator.userActivation.hasBeenActive;
  if (!active) { pending = { out, lang: lg }; return Promise.resolve(); }   // wait for the first tap
  return play(out, lg, orig);
}
// the first tap anywhere plays whatever was waiting (e.g. the home-screen greeting)
["pointerdown", "keydown", "touchstart"].forEach((ev) => W.addEventListener?.(ev, () => { if (pending) { const p = pending; pending = null; play(p.out, p.lang); } }, { passive: true }));

export const hearAgain = () => speak(lastText, lastLang);
export function slowDown() { rate = Math.max(0.5, rate - 0.2); return hearAgain(); }

// ---------- listening ----------
export const canListen = () => !!(W.SpeechRecognition || W.webkitSpeechRecognition);
const MIC = { "not-allowed": "Please allow the microphone.", "service-not-allowed": "Please allow the microphone.", "no-speech": "I did not hear anything.", network: "Voice needs the internet.", "audio-capture": "No microphone found." };
let rec = null;
export function listen(lang = "en-IN") {
  return new Promise((resolve, reject) => {
    const SR = W.SpeechRecognition || W.webkitSpeechRecognition;
    if (!SR) return reject(new Error("Voice input is not supported in this browser. Please use Chrome."));
    synth?.cancel(); stopAudio();            // do not let the mic hear our own voice
    try { rec?.abort(); } catch { /* none running */ }
    const r = new SR(); rec = r;
    r.lang = lang; r.interimResults = false; r.maxAlternatives = 1; r.continuous = false;
    let got = false; const stop = setTimeout(() => { try { r.stop(); } catch { /* ended */ } }, 9000);
    r.onresult = (e) => { got = true; clearTimeout(stop); resolve(e.results[0][0].transcript); };
    r.onerror = (e) => { clearTimeout(stop); reject(new Error(MIC[e.error] || e.error)); };
    r.onend = () => { clearTimeout(stop); if (!got) resolve(""); };
    try { r.start(); } catch (e) { reject(e); }
  });
}

// ---------- yes / no (careful: "not good" is a No) ----------
const tokens = (s) => String(s || "").toLowerCase().split(/[\s,.!?।]+/).filter(Boolean);
const YES_L = /\b(yes|yeah|yep|yup|ok|okay|sure|fine|good|haan|han|haa|ji|theek|thik|avunu|sare|aam|sari|haudu|houdu|ho|hoy)\b/i;
const NO_L = /\b(no|nope|nah|not|never|don't|dont|nahi|nahin|nai|illa|illai|ledu|vaddu|vadu|beda|naahi|nako|nathi|na)\b/i;
const YES_I = ["हाँ", "हां", "ठीक", "అవును", "ఔను", "సరే", "ஆம்", "சரி", "ಹೌದು", "ಸರಿ", "બરાબર", "হ্যাঁ", "ঠিক"];
const NO_I = ["नहीं", "नही", "नाही", "नको", "లేదు", "వద్దు", "இல்லை", "வேண்டாம்", "ಇಲ್ಲ", "ಬೇಡ", "નથી", "নয়"];
const SHORT_YES = ["हा", "हो", "હા"], SHORT_NO = ["ना", "ના", "না"];
const hasNo = (s) => NO_L.test(s) || NO_I.some((w) => s.includes(w)) || tokens(s).some((x) => SHORT_NO.includes(x));
export const isNo = (s) => !!s && hasNo(String(s));
export const isYes = (s) => !!s && !hasNo(String(s)) && (YES_L.test(s) || YES_I.some((w) => s.includes(w)) || tokens(s).some((x) => SHORT_YES.includes(x)));

// ---------- dialects: starter lexicon from the server, cached for offline use ----------
let lex = null;
try { lex = JSON.parse(localStorage.getItem("db_lex")); } catch { /* none yet */ }
export async function loadLexicon(get) { try { lex = await get("/dialect/lexicon"); localStorage.setItem("db_lex", JSON.stringify(lex)); } catch { /* keep cached */ } }
export function interpret(text, dialect = "") {
  const s = (text || "").toLowerCase(); if (!lex) return [];
  const hits = [];
  const phrases = [...Object.entries(lex.dialects?.[dialect] || {}), ...Object.entries(lex.intents || {}).flatMap(([i, ws]) => ws.map((w) => [w, i]))];
  for (const [p, intent] of phrases) { const i = s.indexOf(String(p).toLowerCase()); if (i >= 0) hits.push([i, intent]); }
  hits.sort((a, b) => a[0] - b[0]);
  const out = [...new Set(hits.map((h) => h[1]))];
  if (out.includes("yes") && out.includes("no")) { const last = hits.filter((h) => h[1] === "yes" || h[1] === "no").pop()[1]; return out.filter((x) => x !== "yes" && x !== "no").concat(last); }
  return out;
}
export const saysYes = (s, d) => !isNo(s) && (interpret(s, d).includes("yes") || isYes(s));
export const saysNo = (s, d) => interpret(s, d).includes("no") || isNo(s);

// Ask a yes/no question, wait until it has been spoken, then listen. null = not understood (caller shows buttons).
export async function confirmByVoice(question, lang = "en-IN", dialect = "") {
  await speak(question, lang);
  if (!canListen()) return null;
  try { const s = await listen(lang); if (!s) return null; if (saysNo(s, dialect)) return false; if (saysYes(s, dialect)) return true; } catch { /* ignore */ }
  return null;
}

// ---------- numbers and readings ----------
const DIGITS = { zero: 0, oh: 0, one: 1, two: 2, three: 3, four: 4, five: 5, six: 6, seven: 7, eight: 8, nine: 9,
  शून्य: 0, एक: 1, दो: 2, तीन: 3, चार: 4, पांच: 5, पाँच: 5, छह: 6, छः: 6, सात: 7, आठ: 8, नौ: 9 };
const asciiDigits = (s) => String(s || "").replace(/[०-९]/g, (c) => c.charCodeAt(0) - 0x966).replace(/[౦-౯]/g, (c) => c.charCodeAt(0) - 0xc66);
export function parseDigits(text) {
  return asciiDigits(text).toLowerCase().split(/[\s,.-]+/).map((w) => (/^\d+$/.test(w) ? w : w in DIGITS ? String(DIGITS[w]) : "")).join("");
}
// "My BP is 140 over 90" / "sugar is 180"
export function parseVital(text) {
  const s = asciiDigits(text).toLowerCase();
  const nums = (s.match(/\d+(\.\d+)?/g) || []).map(Number);
  if (/bp|pressure/.test(s) && nums.length >= 2) return { kind: "bp", value1: nums[0], value2: nums[1] };
  if (/sugar|glucose/.test(s) && nums.length) return { kind: "sugar", value1: nums[0] };
  if (/oxygen|spo2/.test(s) && nums.length) return { kind: "spo2", value1: nums[0] };
  if (/pulse|heart rate/.test(s) && nums.length) return { kind: "pulse", value1: nums[0] };
  return null;
}

// ---------- voice navigation ----------
const NAV = [
  ["meds", /medicine|tablet|pill|dawai|dawa|goli|दवा|दवाई|మందులు|మాత్రలు|மருந்து|ಗುಳಿಗೆ|ಔಷಧಿ|औषध|ગોળી|ওষুধ/i],
  ["checkin", /check.?in|how am i|feeling|हालचाल|चेक.?इन|ఎలా ఉన్నారు|బాగున్నా|நலம்|ಆರೋಗ್ಯ|ಕ್ಷೇಮ|कसे आहात|ખબર|কেমন/i],
  ["doctor", /which doctor|कौन.?सा डॉक्टर|ఏ డాక్టర్/i],
  ["health", /\bbp\b|blood pressure|sugar|glucose|vitals|appointment|doctor|शुगर|बीपी|రక్తపోటు|சர்க்கரை|ರಕ್ತದೊತ್ತಡ|ತಪಾಸಣೆ|તપાસ|ডাক্তার/i],
  ["sharing", /share|who can see|privacy|consent|गोपनीयता|ఎవరు చూడవచ్చు|பகிர்வு|ಯಾರು ನೋಡಬಹುದು|गोपनीय|સુરક્ષા|শেয়ার/i],
  ["records", /record|report|lab|test|history|locker|कागजात|రిపోర్టు|பதிவு|ದಾಖಲೆ|अहवाल|રિપોર્ટ|নথি/i],
  ["companion", /companion|talk|friend|chat|music|bhajan|গান|गाना|பாடல்|ಸಂಗೀತ|बातचीत|સાથી/i],
  ["safety", /safe|scam|fraud|police|help|alert|धोखा|భద్రత|பாதுகாப்பு|ರಕ್ಷಣೆ|सुरक्षा|સલામતી|বিপদ/i],
  ["daily", /learn|pension|scheme|government|लाभ|యోజన|திட்டம்|ಯೋಜನೆ|યોજના|সুবিধা/i],
  ["community", /community|friends|rooms|group|दोस्त|స్నేహితులు|நண்பர்கள்|ಸ್ನೇಹಿತರು|મિત્રો|বন্ধু/i],
  ["settings", /setting|font|speed|volume|भाषा|सेटिंग|భాష|அமைப்புகள்|ಸಂಯೋಜನೆ|ભાષા|সেটিংস/i],
  ["pending", /pending|approval|please check|मंजूर|बाकी|మంజూరు|சரிபார்க்க/i],
  ["home", /home|back|main|start|घर|హోమ్|முகப்பு|ಮನೆ|મુખ્ય|শুরু/i],
];
export function voiceNav(text) {
  if (!text) return null;
  const s = text.trim().toLowerCase();
  for (const [route, re] of NAV) if (re.test(s)) return route;
  return null;
}

// speech-to-text for dictation fields
export async function dictate(lang) { try { return await listen(lang); } catch { return ""; } }
