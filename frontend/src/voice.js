export const LANGUAGES = [
  { code: "en-IN", label: "English", native: "English" },
  { code: "hi-IN", label: "Hindi", native: "हिन्दी" },
  { code: "te-IN", label: "Telugu", native: "తెలుగు" },
  { code: "ta-IN", label: "Tamil", native: "தமிழ்" },
  { code: "kn-IN", label: "Kannada", native: "ಕನ್ನಡ" },
  { code: "mr-IN", label: "Marathi", native: "मराठी" },
  { code: "gu-IN", label: "Gujarati", native: "ગુજરાતી" },
  { code: "bn-IN", label: "Bengali", native: "বাংলা" }
];

let lastText = "", lastLang = "en-IN", rate = 0.9;

export const setRate = (r) => { rate = r; };
export const getRate = () => rate;

export function speak(text, lang = lastLang) {
  if (!text) return;
  lastText = text;
  lastLang = lang;
  window.dispatchEvent(new CustomEvent("db-caption", { detail: text }));
  if (!("speechSynthesis" in window)) return;
  window.speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.lang = lang;
  u.rate = rate;
  window.speechSynthesis.speak(u);
}

export const hearAgain = () => speak(lastText, lastLang);
export function slowDown() {
  rate = Math.max(0.5, rate - 0.2);
  hearAgain();
}

export const canListen = () => !!(window.SpeechRecognition || window.webkitSpeechRecognition);

export function listen(lang = "en-IN") {
  return new Promise((resolve, reject) => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) return reject(new Error("Voice input is not supported in this browser"));
    const r = new SR();
    r.lang = lang;
    r.interimResults = false;
    r.maxAlternatives = 3;
    r.onresult = (e) => {
      const transcript = e.results[0][0].transcript;
      resolve(transcript);
    };
    r.onerror = (e) => reject(new Error(e.error));
    r.onend = () => resolve("");
    try {
      r.start();
    } catch (e) {
      reject(e);
    }
  });
}

// Multilingual affirmative check
export function isYes(text) {
  if (!text) return false;
  const t = text.trim().toLowerCase();
  return /yes|yeah|yep|ok|okay|fine|good|हाँ|ठीक|haan|theek|అవును|సరే|avunu|sare|ஆம்|சரி|aam|sari|ಹೌದು|ಸರಿ|haudu|हो|ho|હા|બરાબર|ha|barabar|হ্যাঁ|thik/i.test(t);
}

// Multilingual negative check
export function isNo(text) {
  if (!text) return false;
  const t = text.trim().toLowerCase();
  return /no|nope|nah|not|नहीं|nai|నహి|వద్దు|లేదు|vadu|ledu|இல்லை|வேண்டாம்|illai|vendaam|ಬೇಡ|ಇಲ್ಲ|beda|illa|नाही|नको|naahi|nako|ના|નથી|na|nathi|না/i.test(t);
}

// Helper for Health.jsx to ask a question and get a Yes/No response
export async function confirmByVoice(prompt, lang = "en-IN") {
  if (prompt) speak(prompt, lang);
  
  if (!canListen()) return false;
  
  // Give the voice synthesis a moment to speak before listening
  await new Promise(resolve => setTimeout(resolve, 2500));
  
  try {
    const ans = await listen(lang);
    return isYes(ans);
  } catch {
    return false;
  }
}

// Multilingual keyword navigation map for all 8 languages + English
const NAV = [
  ["meds", /medicine|tablet|pill|dawai|dawa|goli|दवा|दवाई|మందులు|మాత్రలు|மருந்து|ಗುಳಿಗೆ|ಔಷಧಿ|औषध|ગોળી|ওষুধ/i],
  ["checkin", /check.?in|how am i|feeling|well|हालचाल|चेक.?इन|ఎలా ఉన్నారు|బాగున్నా|நலம்|ಆರೋಗ್ಯ|ಕ್ಷೇಮ|कसे आहात|ખબર|কেমন/i],
  ["health", /bp|blood pressure|sugar|glucose|vitals|appointment|doctor|शुगर|बीपी|రక్తపోటు|சர்க்கரை|ರಕ್ತದೊತ್ತಡ|तಪಾಸಣೆ|તપાસ|ডাক্তার/i],
  ["sharing", /share|who can see|privacy|consent|गोपनीयता|ఎవరు చూడవచ్చు|பகிர்வு|ಯಾರು ನೋಡಬಹುದು|गोपनीय|સુરક્ષા|শেয়ার/i],
  ["records", /record|report|lab|test|history|locker|कागजात|రిపోర్టు|பதிவு|ದಾಖಲೆ|अहवाल|રિપોર્ટ|নথি/i],
  ["companion", /companion|talk|friend|chat|music|bhajan|গান|गाना|பாடல்|ಸಂಗೀತ|बातचीत|સાથી/i],
  ["safety", /safe|scam|fraud|police|help|alert|धोखा|భద్రత|பாதுகாப்பு|ರಕ್ಷಣೆ|सुरक्षा|સલામતી|বিপদ/i],
  ["daily", /learn|pension|scheme|government|लाभ|యోజన|திட்டம்|ಯೋಜನೆ|યોજના|সুবিধা/i],
  ["community", /community|friends|rooms|group|दोस्त|స్నేహితులు|நண்பர்கள்|ಸ್ನೇಹಿತರು|મિત્રો|বন্ধু/i],
  ["settings", /setting|font|speed|volume|भाषा|सेटिंग|భాష|அமைப்புகள்|ಸಂಯೋಜನೆ|ભાષા|সেটিংস/i],
  ["pending", /check|pending|approval|మంజూరు|बाकी|சரிபார்க்க/i],
  ["home", /home|back|main|start|घर|హోమ్|முகப்பு|ಮನೆ|મુખ્ય|শুরু/i]
];

export function voiceNav(text) {
  if (!text) return null;
  const t = text.trim().toLowerCase();
  for (const [route, regex] of NAV) {
    if (regex.test(t)) return route;
  }
  return null;
}

export async function dictate(lang) {
  try {
    return await listen(lang);
  } catch {
    return "";
  }
}
