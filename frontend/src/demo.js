// Demo backend: answers the app's API calls with sample data so the live site works with no server.
// Sample people and numbers are made up. Unknown calls fail politely instead of returning wrong data.
const at = (d = 0, h = 8) => { const x = new Date(); x.setDate(x.getDate() - d); x.setHours(h, 0, 0, 0); return x.toISOString().slice(0, 19); };
const day = (n) => { const x = new Date(); x.setDate(x.getDate() + n); x.setHours(11, 0, 0, 0); return x.toISOString().slice(0, 19); };
const base = { language: "en-IN", channel: "app" };
const USERS = {
  elder: { id: 1, name: "Sarala", role: "elder", ...base, settings: { font_scale: 1, high_contrast: false, captions: true, vibrate_flash: false, speech_rate: 0.9, lite_mode: "auto" } },
  family: { id: 2, name: "Rohan (son)", role: "family", ...base },
  chw: { id: 3, name: "Meena (ASHA)", role: "chw", ...base },
  partner: { id: 4, name: "Seva Trust", role: "partner", ...base },
};
const TYPES = { mood: "my mood", checkins: "my daily check-ins", medicines: "my medicines", vitals: "my BP and sugar readings", emergency_card: "my emergency card", report: "my weekly report", imfine: "my 'I am fine' message", sos: "emergency alerts", messages: "messages", video: "video calls" };
const st = {
  settings: { font_scale: 1, high_contrast: false, captions: true, vibrate_flash: false, speech_rate: 0.9, lite_mode: "auto", dialect: "", nudges: {}, pharmacy_phone: "", family_doctor_phone: "", faith: "", community: false, aggregate_opt_in: false, region: "", activity_tracking: false },
  meds: [
    { id: 1, name: "Metformin 500mg", tablets: 1, times: ["09:00", "21:00"], color: "white", stock: 6, days_left: 3, low_stock: true },
    { id: 2, name: "Amlodipine 5mg", tablets: 1, times: ["09:00"], color: "pink", stock: 24, days_left: 24, low_stock: false },
  ],
  taken: [], nid: 100,
  vitals: [{ kind: "bp", value1: 148, value2: 94, flagged: true, source: "manual", at: at(0, 7) }, { kind: "sugar", value1: 132, flagged: false, source: "manual", at: at(1, 7) }, { kind: "bp", value1: 138, value2: 88, flagged: false, source: "manual", at: at(2, 7) }, { kind: "spo2", value1: 97, flagged: false, source: "manual", at: at(3, 7) }],
  appts: [{ id: 1, doctor: "Dr. Reddy (Diabetologist)", kind: "visit", at: day(2), speak: "You see Dr. Reddy in two days." }],
  card: { blood_group: "B+", allergies: "Penicillin", conditions: "Diabetes, High BP", doctor_name: "Dr. Reddy", doctor_phone: "9800000000", contacts: "Rohan:9811111111; Priya:9822222222", medicines: ["Metformin 500mg", "Amlodipine 5mg"] },
  grants: [{ id: 1, grantee: "Rohan", relation: "son", data_type: "medicines", scope: "view", expires_at: null }, { id: 2, grantee: "Rohan", relation: "son", data_type: "report", scope: "view", expires_at: null }, { id: 3, grantee: "Rohan", relation: "son", data_type: "sos", scope: "escalate", expires_at: null }],
  proposals: [{ id: 1, speak: "Your son Rohan would like to see your mood for 30 days. Do you agree?", items: [{ data_type: "mood", scope: "view" }], days: 30 }],
  diary: [{ id: 1, at: at(1), text: "Knee pain at night" }], questions: [],
};
const due = () => st.meds.flatMap((m) => m.times.slice(0, m.id === 1 ? 1 : 1).map((s) => ({ medicine_id: m.id, name: m.name, tablets: m.tablets, slot: s, snoozed: 0, speak: `Time for ${m.name}.`, offer_tell_family: false }))).filter((d) => !st.taken.includes(d.medicine_id + d.slot));
const report = () => ({ adherence_pct: 86, doses_taken: 24, doses_expected: 28, checkins: 6, good_days: 5, good_news: ["She walked every day this week", "Sugar readings were steady"] });
const R = [];
const on = (m, re, fn) => R.push([m, re, fn]);

on("POST", /^\/auth\/request-otp$/, () => ({ dev_otp: "123456" }));
on("POST", /^\/auth\/verify$/, (b) => ({ token: "demo-" + (b.role === "elder" ? "elder" : b.role || "family"), user: {} }));
on("GET", /^\/me$/, (b, q, t) => USERS[(t || "").replace("demo-", "")] || USERS.elder);
on("PATCH", /^\/me$/, () => ({ ok: true }));
on("GET", /^\/dialect\/lexicon$/, () => ({ intents: { yes: ["yes", "haan"], no: ["no", "nahi"] }, dialects: {} }));
on("GET", /^\/lite\/home$/, () => ({ medicines: st.meds.map((m) => ({ name: m.name, times: m.times.join(","), tablets: m.tablets })), due: due(), appointments: st.appts, reminders: [{ say: "It is your daughter Priya's birthday tomorrow." }], nudges: [{ say: "A glass of water now would be good." }], unread_messages: 0, pending: st.proposals.length, disaster: false }));
on("GET", /^\/video\/incoming$/, () => []);
on("POST", /^\/sync\/batch$/, () => ({ results: [] }));
on("GET", /^\/medicines\/due$/, () => due());
on("GET", /^\/medicines$/, () => st.meds);
on("POST", /^\/medicines$/, (b) => { st.meds.push({ id: ++st.nid, name: b.name, tablets: b.tablets, times: String(b.times).split(","), color: b.color, stock: b.stock, days_left: b.stock, low_stock: false }); return { ok: true }; });
on("POST", /^\/medicines\/(\d+)\/taken$/, (b, q, t, m) => { st.taken.push(+m[1] + b.slot); return { ok: true }; });
on("POST", /^\/medicines\/\d+\/snooze$/, () => ({ offer_tell_family: false }));
on("POST", /^\/medicines\/\d+\/missed$/, () => ({ speak: "Noted. Please do not double up. Ask your doctor if unsure." }));
on("GET", /^\/medicines\/interactions$/, () => ({ speak: "I see no known problem between your two medicines. Please confirm with your doctor." }));
on("GET", /^\/medicines\/generic\//, () => ({ say: "A generic version usually costs much less. Ask your pharmacist." }));
on("POST", /^\/refills$/, () => ({ id: 1, speak: "Shall I send a refill request to your pharmacy?" }));
on("POST", /^\/refills\/\d+\/confirm$/, () => ({ note: "Request noted (demo).", open: "" }));
on("POST", /^\/prescriptions\/parse$/, (b) => ({ candidates: b.text ? [{ name: "Metformin", tablets: 1 }] : [] }));
on("POST", /^\/pillbox\/verify$/, () => ({ ok: true, speak: "Your tablets look right for this time.", note: "demo" }));
on("POST", /^\/checkin$/, (b) => ({ pattern_note: "You have felt good on most days this week.", ask_to_inform_family_alert_id: b.needs_help || b.mood === "low" ? 5 : null }));
on("POST", /^\/alerts\/\d+\/respond$/, () => ({ ok: true }));
on("GET", /^\/vitals$/, () => st.vitals);
on("POST", /^\/vitals\/voice$/, (b) => (/\d/.test(b.text || "") ? { understood: true, speak: `I heard ${b.text}. Shall I save it?`, pending_id: 1 } : { understood: false, speak: "Please say it like: B P is 140 over 90." }));
on("POST", /^\/pending\/\d+$/, () => ({ flagged: false, advice: "" }));
on("POST", /^\/devices\/readings$/, () => ({ flagged: false }));
on("GET", /^\/pending$/, () => []);
on("GET", /^\/services\/pending$/, () => []);
on("GET", /^\/consents\/proposals$/, () => st.proposals);
on("POST", /^\/consents\/proposals\/(\d+)$/, (b, q, t, m) => { const p = st.proposals.find((x) => x.id === +m[1]); st.proposals = st.proposals.filter((x) => x.id !== +m[1]); if (b.approve && p) p.items.forEach((i) => st.grants.push({ id: ++st.nid, grantee: "Rohan", relation: "son", data_type: i.data_type, scope: i.scope, expires_at: null })); return { ok: true }; });
on("GET", /^\/appointments$/, () => st.appts);
on("POST", /^\/appointments$/, (b) => { st.appts.push({ id: ++st.nid, doctor: b.doctor, kind: "visit", at: b.at }); return { ok: true }; });
on("GET", /^\/emergency-card$/, () => st.card);
on("PUT", /^\/emergency-card$/, (b) => { Object.assign(st.card, b); return st.card; });
on("GET", /^\/reports\/week$/, report);
on("POST", /^\/doctor\/suggest$/, (b) => {
  const s = (b.symptom || "").toLowerCase();
  const d = /chest|heart|breath/.test(s) ? ["Cardiologist", "Chest and heart symptoms need quick attention.", "If the pain is severe or sudden, call 108 now."] : /sugar|thirst|urine/.test(s) ? ["Diabetologist", "Your symptoms may relate to blood sugar.", ""] : /knee|joint|back|bone/.test(s) ? ["Orthopaedic doctor", "Joint and bone problems are seen by this doctor.", ""] : /eye|vision/.test(s) ? ["Eye doctor", "Eye problems are seen by an ophthalmologist.", ""] : ["General physician", "A general physician is a good first visit.", ""];
  return { doctor: d[0], why: d[1], urgent_note: d[2], disclaimer: "This is a suggestion, not a diagnosis." };
});
on("GET", /^\/settings$/, () => st.settings);
on("PUT", /^\/settings$/, (b) => Object.assign(st.settings, b));
on("GET", /^\/pricing$/, () => ({ tiers: [{ id: "free", price_per_month: 0, includes: ["SOS", "reminders", "check-in"] }, { id: "family", price_per_month: 199, includes: ["family portal", "video calls"] }], note: "Safety features stay free." }));
on("GET", /^\/billing\/\d+$/, () => ({ tier: "free" }));
on("GET", /^\/devices$/, () => []);
on("GET", /^\/consents\/types$/, () => TYPES);
on("GET", /^\/consents$/, () => st.grants);
on("POST", /^\/consents$/, (b) => { st.grants.push({ id: ++st.nid, grantee: b.grantee_name || b.grantee_phone, relation: b.relation, data_type: b.data_type, scope: b.scope, expires_at: b.days ? "soon" : null }); return { ok: true }; });
on("DELETE", /^\/consents\/(\d+)$/, (b, q, t, m) => { st.grants = st.grants.filter((g) => g.id !== +m[1]); return { ok: true }; });
on("POST", /^\/consents\/revoke-by-voice$/, () => { st.grants = st.grants.filter((g) => g.data_type !== "mood"); return { speak: "Okay, I stopped sharing your mood." }; });
on("GET", /^\/consents\/log$/, () => ({ sentences: ["Rohan looked at your medicines yesterday.", "Dr. Reddy has not seen anything.", "You are sharing three things right now."] }));
on("POST", /^\/consents\/share-with-doctor$/, (b) => ({ shared_with: b.doctor_name || "the doctor", days: b.days || 7 }));
on("POST", /^\/sos$/, () => ({ contacts_notified: 2 }));
on("POST", /^\/fall$/, () => ({ alert_id: 7 }));
on("POST", /^\/imfine$/, (b, q) => (q.includes("approve") ? { speak: "I told your family you are fine." } : { draft: "Tell Rohan and Priya: “I am fine today”?", speak: "Shall I tell your family you are fine?" }));
on("GET", /^\/symptoms$/, () => st.diary);
on("POST", /^\/symptoms$/, (b) => { st.diary.unshift({ id: ++st.nid, at: at(0), text: b.text }); return { ok: true }; });
on("DELETE", /^\/symptoms\/(\d+)$/, (b, q, t, m) => { st.diary = st.diary.filter((x) => x.id !== +m[1]); return { ok: true }; });
on("GET", /^\/previsit$/, () => ({ period_days: 30, medicines: st.meds, missed_doses: [{ medicine: "Metformin", missed_approx: 3 }], symptoms: st.diary, vitals: st.vitals, pain_days: 4, questions: st.questions, disclaimer: "A summary to help the conversation, not medical advice." }));
on("POST", /^\/previsit\/questions$/, (b) => { st.questions.push(b.question); return { ok: true }; });
on("GET", /^\/scam\/tips$/, () => ({ tip: "No bank or government office will ever ask for your OTP." }));
on("POST", /^\/scam\/check$/, (b) => { const bad = /otp|kyc|blocked|lottery|prize|click|link|urgent|upi|pin/i.test(b.text || ""); return bad ? { level: "high", reasons: ["Asks for an OTP, PIN or a link", "Creates urgency"], advice: "Do not reply or click. Call 1930.", ask_to_inform_alert_id: 9 } : { level: "low", reasons: [], advice: "Still, never share your OTP.", ask_to_inform_alert_id: null }; });
on("GET", /^\/helplines$/, () => [{ name: "Ambulance", number: "108" }, { name: "Emergency", number: "112" }, { name: "Elder helpline", number: "14567" }]);
on("GET", /^\/weather\/advice/, () => ({ temp_c: 36, aqi: 112, advice: ["It is hot. Drink water often.", "Avoid going out at noon."], speak: "It is 36 degrees. Please drink water often.", suggest_disaster_mode: false }));
on("GET", /^\/home-safety$/, () => ({ score: 2, total: 4, items: [{ id: 1, text: "Night light in the bathroom", ok: true }, { id: 2, text: "No loose rugs", ok: true }, { id: 3, text: "Grab bars", ok: null }, { id: 4, text: "Medicines kept in one place", ok: false }], to_fix: ["Medicines kept in one place"] }));
on("GET", /^\/disaster$/, () => ({ on: false }));
on("POST", /^\/assistant\/intent$/, (b) => (/sos|help|emergency/i.test(b.text) ? { speak: "Shall I alert your family?", action: { type: "sos", needs_confirm: true } } : { speak: "Demo: I can call family, set alarms, and read the news. Try “help”.", action: null }));
on("GET", /^\/lessons$/, () => [{ id: 1, title: "Make a video call" }]);
on("GET", /^\/lessons\/1$/, () => ({ title: "Make a video call", steps: ["Open the app.", "Tap your son's name.", "Tap the video button."], quiz: [{ q: "Which button starts a video call?", options: ["Camera", "Speaker"], answer: 0 }] }));
on("GET", /^\/schemes/, () => ({ matches: [{ id: 1, name: "Ayushman Bharat (PM-JAY)", why: "Health cover for eligible families.", docs: ["Aadhaar", "Ration card"], where: "Empanelled hospital or CSC", verify: true }], disclaimer: "Always confirm at the official office." }));
on("GET", /^\/inbox$/, () => [{ id: 1, text: "Sarala took her morning medicines.", at: at(0, 9), channel: "app" }]);
// ---- family portal ----
on("GET", /^\/family\/elders$/, () => [{ id: 1, name: "Sarala Devi", local_time: "10:42", timezone: "IST" }]);
on("GET", /^\/family\/elders\/1\/summary$/, () => ({ shared: { imfine: true, report: report(), mood: [{ at: at(5), mood: "good" }, { at: at(4), mood: "good" }, { at: at(3), mood: "okay" }, { at: at(2), mood: "good" }, { at: at(1), mood: "low" }, { at: at(0), mood: "good" }], mood_trend: { note: "A low day yesterday, otherwise steady." }, checkins: [{ at: at(0), mood: "good", pain: "none", needs_help: false }, { at: at(1), mood: "low", pain: "mild", needs_help: false }], medicines: st.meds.map((m) => ({ id: m.id, name: m.name, tablets: m.tablets, low_stock: m.low_stock, stock: m.stock })), vitals: st.vitals, appointments: st.appts.map((a) => ({ doctor: a.doctor, kind: a.kind, at: a.at })) }, not_shared: ["symptom diary", "documents"] }));
on("GET", /^\/family\/call-nudges$/, () => [{ elder_id: 1, say: "Sarala hasn't had a call in 3 days. Good time to ring." }]);
on("GET", /^\/family\/elders\/1\/digest$/, () => ({ say: "Great week: she took 86% of her medicines and walked daily." }));
on("GET", /^\/care-team/, () => ({ members: [{ id: 2, name: "Rohan", role: "primary", relation: "son" }, { id: 5, name: "Priya", role: "sibling", relation: "daughter" }, { id: 6, name: "Dr. Reddy", role: "doctor", relation: "doctor" }], responsible_this_week: 2 }));
on("GET", /^\/tasks/, () => [{ id: 1, title: "Take Amma for eye check-up", due_on: day(5).slice(0, 10), claimed_by: null, done: false }]);
on("GET", /^\/expenses/, () => ({ total: 1800, items: [{ id: 1, what: "Medicines", amount: 1800 }], settle_up: [] }));
on("GET", /^\/caregiver\/wellbeing\/questions$/, () => ({ scale: "quick check", questions: ["Do you feel tired from caring?", "Do you get time for yourself?"] }));
on("POST", /^\/caregiver\/wellbeing$/, () => ({ level: "moderate", tips: ["Share tasks on the board", "Take a short walk"], note: "This is not a diagnosis." }));
on("POST", /^\/video\/call\//, () => ({ room_url: "https://meet.jit.si/aarogyasaathi-demo", auto_answered: true }));
on("POST", /^\/family\/elders\/\d+\/called$/, () => ({ ok: true }));
// ---- partner / health worker ----
on("GET", /^\/orgs\/me\/elders$/, () => [{ id: 1, name: "Sarala Devi" }]);
on("POST", /^\/chw\/visit$/, (b) => ({ vitals: (b.vitals || []).length, checkin: !!b.checkin }));
on("POST", /^\/orgs$/, () => ({ code: "SEVA-2026" }));
on("GET", /^\/insights\/aggregate$/, () => ({ note: "Anonymous. Areas with too few people are hidden.", regions: [{ region: "Kukatpally", elders: 42, low_mood_pct: 11, flagged_reading_pct: 18 }], suppressed_regions: 2 }));

export async function demoCall(method, rawPath, body, token) {
  await new Promise((r) => setTimeout(r, 120));
  const [p, qs = ""] = rawPath.split("?");
  for (const [m, re, fn] of R) { const x = p.match(re); if (m === method && x) return JSON.parse(JSON.stringify(fn(body || {}, qs, token, x))); }
  throw new Error("This part is not in the live demo.");
}
