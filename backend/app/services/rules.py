"""Small, deterministic, auditable rule engines. No diagnosis anywhere."""
import math
import re
from datetime import date, datetime, timedelta

# ---------- prescription text -> candidate medicines (elder must confirm each) ----------
_FREQ = {"od": ["08:00"], "bd": ["08:00", "20:00"], "bid": ["08:00", "20:00"], "tds": ["08:00", "14:00", "20:00"], "tid": ["08:00", "14:00", "20:00"],
         "qid": ["07:00", "12:00", "17:00", "22:00"], "hs": ["21:00"], "qd": ["08:00"]}


def parse_prescription(text: str) -> list[dict]:
    out = []
    for line in text.splitlines():
        l = line.strip()
        m = re.match(r"^(?:tab(?:let)?\.?|cap(?:sule)?\.?|syp\.?|inj\.?)?\s*([A-Za-z][A-Za-z\-]{2,}(?:\s?\d+\s?(?:mg|mcg|g|ml))?)", l, re.I)
        if not m or not re.search(r"\d|\b(od|bd|tds|bid|tid|qid|hs|daily|morning|night|once|twice|thrice)\b", l, re.I):
            continue
        low = l.lower()
        times = None
        pat = re.search(r"\b(\d)\s*-\s*(\d)\s*-\s*(\d)\b", low)  # 1-0-1 morning/noon/night
        if pat:
            times = [t for f, t in zip(pat.groups(), ["08:00", "14:00", "21:00"]) if f != "0"]
        for k, v in _FREQ.items():
            if times is None and re.search(rf"\b{k}\b", low):
                times = v
        if times is None:
            times = ["08:00", "20:00"] if re.search(r"twice", low) else ["08:00", "14:00", "20:00"] if re.search(r"thrice", low) else ["08:00"]
        days = re.search(r"(?:x|for)\s*(\d+)\s*(?:days|d)\b", low)
        tabs = re.search(r"\b(\d)\s*(?:tab|tablet|cap)", low)
        out.append({"name": m.group(1).strip(), "tablets": int(tabs.group(1)) if tabs else 1, "times": ",".join(times),
                    "stock": (int(days.group(1)) * len(times)) if days else 0, "source_line": l})
    return out


# ---------- vitals from speech ----------
def parse_vital(text: str) -> dict | None:
    t = text.lower()
    nums = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", t)]
    if re.search(r"\bbp\b|pressure", t) and len(nums) >= 2:
        return {"kind": "bp", "value1": nums[0], "value2": nums[1]}
    if re.search(r"sugar|glucose", t) and nums:
        return {"kind": "sugar", "value1": nums[0]}
    if re.search(r"oxygen|spo2|saturation", t) and nums:
        return {"kind": "spo2", "value1": nums[0]}
    if re.search(r"pulse|heart rate", t) and nums:
        return {"kind": "pulse", "value1": nums[0]}
    return None


def readback(kind: str, p: dict) -> str:
    if kind == "vital":
        v = f"{p['value1']:g}" + (f" over {p['value2']:g}" if p.get("value2") else "")
        return f"I heard {p['kind'].upper()} {v}. Shall I save it?"
    if kind == "medicine":
        return f"{p['name']}, {p.get('tablets', 1)} tablet at {p.get('times', '')}. Shall I add this medicine?"
    if kind == "visit_note":
        return "I wrote down your doctor's advice in simple words. Shall I save it?"
    if kind == "appointment":
        return f"Visit with {p.get('doctor')} on {p.get('at')}. Shall I add it?"
    return "Shall I save this?"


# ---------- doctor advice -> simple instructions ----------
def simplify_visit_note(text: str) -> dict:
    sents = [s.strip() for s in re.split(r"[.\n;]+", text) if s.strip()]
    take, avoid, follow, other = [], [], [], []
    for s in sents:
        l = s.lower()
        (follow if re.search(r"come (back|again)|follow.?up|review|next visit|after \d+ (days|weeks|months)", l) else
         avoid if re.search(r"\b(avoid|do not|don't|stop|no )", l) else
         take if re.search(r"\b(take|tablet|capsule|syrup|apply|after food|before food|daily|twice|night|morning)\b", l) else other).append(s)
    wk = re.search(r"(\d+)\s*(day|week|month)", " ".join(follow).lower())
    follow_in = None
    if wk:
        follow_in = int(wk.group(1)) * {"day": 1, "week": 7, "month": 30}[wk.group(2)]
    return {"take": take, "avoid": avoid, "follow_up": follow, "other": other, "follow_up_in_days": follow_in}


# ---------- lab values: plain language, never diagnose ----------
LAB_RANGES = {  # typical adult reference ranges; labs print their own - those win when supplied
    "hemoglobin": (12.0, 17.5, "g/dL", "Haemoglobin carries oxygen in your blood."),
    "fasting sugar": (70, 100, "mg/dL", "Fasting blood sugar."), "hba1c": (4.0, 5.6, "%", "Average sugar over about 3 months."),
    "cholesterol": (0, 200, "mg/dL", "Total cholesterol."), "ldl": (0, 100, "mg/dL", "'Bad' cholesterol."),
    "hdl": (40, 100, "mg/dL", "'Good' cholesterol."), "triglycerides": (0, 150, "mg/dL", "Fats in the blood."),
    "creatinine": (0.6, 1.3, "mg/dL", "A kidney function marker."), "tsh": (0.4, 4.5, "mIU/L", "A thyroid marker."),
    "vitamin d": (30, 100, "ng/mL", "Vitamin D level."), "uric acid": (3.0, 7.0, "mg/dL", "Uric acid level."),
}


def read_labs(text: str) -> list[dict]:
    out = []
    low = text.lower().replace("fasting blood sugar", "fasting sugar").replace("haemoglobin", "hemoglobin")
    for name, (lo, hi, unit, about) in LAB_RANGES.items():
        m = re.search(rf"{re.escape(name)}\D{{0,15}}?(\d+(?:\.\d+)?)", low)
        if not m:
            continue
        v = float(m.group(1))
        pos = "below the usual range" if v < lo else "above the usual range" if v > hi else "within the usual range"
        out.append({"test": name, "value": v, "unit": unit, "usual": f"{lo:g}-{hi:g}", "position": pos, "about": about,
                    "say": f"Your {name} is {v:g} {unit}. This is {pos} ({lo:g}-{hi:g}). {about} "
                           + ("Please show this report to your doctor; only a doctor can say what it means." if pos != "within the usual range"
                              else "Your doctor will still review the full report.")})
    return out


# ---------- information-only medicine interactions / generics ----------
INTERACTIONS = [  # pairs flagged for 'ask your doctor or pharmacist'. Intentionally short, conservative.
    ({"aspirin", "warfarin"}, "Both can increase bleeding."), ({"ibuprofen", "aspirin"}, "Taken together they can irritate the stomach and affect the heart-protecting effect of aspirin."),
    ({"diclofenac", "aspirin"}, "Both can irritate the stomach."), ({"amlodipine", "simvastatin"}, "Amlodipine can raise simvastatin levels."),
    ({"metformin", "alcohol"}, "Alcohol with metformin can be unsafe."), ({"sildenafil", "nitroglycerin"}, "This combination can drop blood pressure sharply."),
    ({"clopidogrel", "omeprazole"}, "Omeprazole may reduce how well clopidogrel works."), ({"enalapril", "potassium"}, "Together they can raise potassium."),
    ({"lisinopril", "potassium"}, "Together they can raise potassium."), ({"ibuprofen", "enalapril"}, "Pain-killers like ibuprofen can reduce BP-medicine effect and strain kidneys."),
]
GENERICS = {"crocin": "paracetamol", "dolo": "paracetamol", "glycomet": "metformin", "pantop": "pantoprazole", "telma": "telmisartan",
            "amlong": "amlodipine", "ecosprin": "aspirin", "atorva": "atorvastatin", "thyronorm": "levothyroxine", "shelcal": "calcium + vitamin D3",
            "combiflam": "ibuprofen + paracetamol", "norvasc": "amlodipine", "voveran": "diclofenac"}


def _norm(n: str) -> str:
    n = n.lower()
    n = re.sub(r"\b\d+\s*(mg|mcg|g|ml)\b", "", n)
    return GENERICS.get(re.sub(r"[^a-z]", " ", n).split()[0] if re.sub(r"[^a-z]", " ", n).split() else n, n).split(" + ")[0].strip()


def interactions(names: list[str]) -> list[dict]:
    ns = {_norm(n) for n in names}
    ns |= {part.strip() for n in names for part in GENERICS.get(n.lower().split()[0], "").split("+") if part.strip()}
    return [{"between": sorted(pair), "note": why, "advice": "Ask your doctor or pharmacist before taking these together. Do not stop any medicine on your own."}
            for pair, why in INTERACTIONS if pair <= ns]


def generic_info(name: str) -> dict:
    key = name.lower().split()[0] if name.split() else ""
    g = GENERICS.get(key)
    return {"brand": name, "generic": g or "", "say": (f"{name} contains {g}. Ask your pharmacist whether a cheaper generic with the same ingredient is suitable for you."
            if g else f"Ask your pharmacist whether {name} has a generic version."), "disclaimer": "Information only. Never switch medicines without your doctor or pharmacist."}


# ---------- scam check ----------
_SCAM = [(r"\botp\b|one.?time password", 3, "Someone is asking for an OTP. Real banks never ask for it."), (r"kyc|pan.*(update|block)|account.*(block|suspend|freez)", 3, "Threat about your account being blocked is a common trick."),
         (r"lottery|you (have )?won|prize|lucky draw|cash ?back", 3, "You cannot win a prize you never entered."), (r"digital arrest|cbi|customs|narcotics|police.*(video|call)|arrest", 4, "Police and agencies never arrest anyone over video call or ask for money."),
         (r"anydesk|teamviewer|quicksupport|screen ?share|remote access", 4, "Never install apps or share your screen on someone's request."), (r"https?://|bit\.ly|tinyurl|click (here|the link)", 2, "Do not tap unknown links."),
         (r"urgent|immediately|within \d+ (hours|minutes)|last chance|today only", 2, "Pressure to hurry is a warning sign."), (r"send money|transfer|pay (a )?(fee|fine|tax|charges)|gift card|upi pin", 3, "Do not send money to people you cannot verify."),
         (r"grandson|grand.?son|nephew.*(accident|jail|hospital)|in trouble", 2, "A 'relative in trouble' call - hang up and call the relative yourself.")]


def scam_check(text: str) -> dict:
    t = text.lower()
    hits = [(w, msg) for pat, w, msg in _SCAM if re.search(pat, t)]
    score = min(10, sum(w for w, _ in hits))
    level = "high" if score >= 5 else "medium" if score >= 3 else "low"
    return {"risk": score, "level": level, "reasons": [m for _, m in hits], "advice": "Never share your OTP, PIN or card number. Hang up and call your bank or family yourself. Cyber-crime helpline: 1930."
            if level != "low" else "No usual scam signs found, but if you feel unsure, ask your family before acting.", "never_share_otp": True}


# ---------- weather / air advice ----------
def weather_advice(temp_c: float | None, aqi: float | None) -> list[str]:
    a = []
    if temp_c is not None:
        if temp_c >= 40: a += ["Very hot today. Stay indoors from 11 am to 4 pm, drink water often, wear light cotton clothes."]
        elif temp_c >= 35: a += ["It is hot. Drink water regularly and avoid walking at midday."]
        elif temp_c <= 8: a += ["Very cold. Wear warm layers, keep your head and feet covered, avoid early-morning walks."]
        elif temp_c <= 14: a += ["It is cold. Keep warm and take your morning walk after the sun is up."]
    if aqi is not None:
        if aqi >= 200: a += ["Air is very unhealthy. Stay indoors, keep windows closed, wear an N95 mask if you must go out."]
        elif aqi >= 150: a += ["Air quality is poor. Avoid long walks outside and wear a mask."]
        elif aqi >= 100: a += ["Air is moderate. People with breathing problems should limit outdoor time."]
    return a or ["Weather and air look comfortable today."]


# ---------- prayer times (astronomical approximation; MWL angles) ----------
def prayer_times(d: date, lat: float, lng: float, tz_hours: float = 5.5, hanafi: bool = False) -> dict:
    n = d.timetuple().tm_yday
    g = 2 * math.pi / 365 * (n - 1)
    decl = 0.006918 - 0.399912 * math.cos(g) + 0.070257 * math.sin(g) - 0.006758 * math.cos(2 * g) + 0.000907 * math.sin(2 * g)
    eqt = 229.18 * (0.000075 + 0.001868 * math.cos(g) - 0.032077 * math.sin(g) - 0.014615 * math.cos(2 * g) - 0.040849 * math.sin(2 * g))
    noon = 12 + tz_hours - lng / 15 - eqt / 60
    la = math.radians(lat)

    def ha(angle_deg):
        x = (math.sin(math.radians(angle_deg)) - math.sin(la) * math.sin(decl)) / (math.cos(la) * math.cos(decl))
        return math.degrees(math.acos(max(-1, min(1, x)))) / 15

    asr_ang = math.degrees(math.atan(1 / ((2 if hanafi else 1) + math.tan(abs(la - decl)))))
    fmt = lambda h: f"{(int(round(h * 60)) // 60) % 24:02d}:{int(round(h * 60)) % 60:02d}"
    return {"fajr": fmt(noon - ha(-18)), "sunrise": fmt(noon - ha(-0.833)), "dhuhr": fmt(noon + 0.0167), "asr": fmt(noon + ha(asr_ang)),
            "maghrib": fmt(noon + ha(-0.833)), "isha": fmt(noon + ha(-17)), "note": "Approximate. Confirm with your local mosque timetable."}


# ---------- tone of check-in words ----------
NEG = ("sad", "lonely", "alone", "tired", "weak", "pain", "worried", "scared", "afraid", "hopeless", "useless", "no use", "sleepless", "cry", "dukhi", "thaka", "akela", "उदास", "अकेला", "थका")
POS = ("happy", "good", "fine", "well", "better", "enjoy", "grateful", "peace", "walk", "khush", "accha", "अच्छा", "खुश")


def tone(note: str) -> int:
    t = note.lower()
    return sum(w in t for w in POS) - sum(w in t for w in NEG)


# ---------- spoken revoke ----------
_TYPE_WORDS = {"mood": ("mood", "feeling", "mizaj"), "checkin": ("check-in", "checkin", "check in"), "medicines": ("medicine", "medicines", "tablet", "dawai", "dawa"),
               "vitals": ("bp", "sugar", "reading", "readings", "vitals", "pressure"), "reports": ("report", "reports"), "appointments": ("visit", "appointment", "visits"),
               "emergency_card": ("emergency card", "card"), "sos": ("emergency", "sos", "alert", "alerts"), "imfine": ("i am fine", "i'm fine", "imfine"),
               "symptoms": ("symptom", "symptoms", "diary"), "documents": ("document", "documents", "records"), "life_story": ("story", "stories"),
               "activity": ("sleep", "activity", "steps")}
RELATIONS = ("son", "daughter", "wife", "husband", "brother", "sister", "grandson", "granddaughter", "grandchild", "doctor", "neighbour", "neighbor", "nurse", "friend", "beta", "beti")


def parse_revoke(text: str) -> dict:
    t = text.lower()
    types = [k for k, ws in _TYPE_WORDS.items() if any(re.search(rf"\b{re.escape(w)}\b", t) for w in ws)]
    rel = next((r for r in RELATIONS if re.search(rf"\b{r}\b", t)), "")
    everything = bool(re.search(r"\b(everything|all|sab kuch|anything)\b", t))
    return {"types": types, "relation": {"beta": "son", "beti": "daughter", "neighbor": "neighbour"}.get(rel, rel), "everything": everything or not types}


# ---------- IDs ----------
def add_months(d: date, n: int) -> date:
    y, m = divmod(d.month - 1 + n, 12)
    y += d.year
    m += 1
    day = min(d.day, [31, 29 if y % 4 == 0 and (y % 100 or y % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1])
    return date(y, m, day)
