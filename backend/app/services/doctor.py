"""Suggests a TYPE of doctor and why. Never diagnoses. Rule-based so it is predictable and auditable."""
RULES = [
    (("chest pain", "chest", "heart", "palpitation", "breathless", "सीने", "ఛాతీ"),
     "Cardiologist", "Chest and breathing symptoms are best checked by a heart specialist.", True),
    (("sugar", "thirst", "diabetes", "tingling feet", "शुगर"),
     "Diabetologist / General Physician", "Sugar-related concerns are looked after by a diabetes doctor.", False),
    (("knee", "joint", "back pain", "bone", "hip", "घुटने", "జాయింట్"),
     "Orthopaedic doctor", "Joint, bone and back pain are handled by an orthopaedic doctor.", False),
    (("eye", "vision", "blurry", "cataract", "आंख"),
     "Ophthalmologist", "Eye and vision changes need an eye specialist.", False),
    (("ear", "hearing", "deaf", "dizzy", "dizziness", "कान"),
     "ENT specialist", "Hearing and balance concerns are seen by an ENT doctor.", False),
    (("cough", "wheez", "asthma", "phlegm", "खांसी"),
     "Pulmonologist / General Physician", "Cough and breathing trouble are seen by a chest doctor.", False),
    (("stomach", "acidity", "vomit", "constipation", "digest", "पेट"),
     "Gastroenterologist / General Physician", "Stomach and digestion issues are seen by a stomach doctor.", False),
    (("sad", "lonely", "sleep", "anxious", "scared", "memory", "forget", "उदास"),
     "Psychiatrist / Counsellor / Geriatrician", "Mood, sleep and memory concerns can be discussed with a counsellor or geriatrician.", False),
    (("skin", "rash", "itch", "त्वचा"),
     "Dermatologist", "Skin problems are seen by a skin doctor.", False),
    (("urine", "kidney", "prostate", "burning"),
     "Urologist / Nephrologist", "Urine-related symptoms are seen by a urinary-tract doctor.", False),
]
DISCLAIMER = "This is only a suggestion about which doctor to meet. DocBuddy cannot diagnose. Please consult a doctor."
URGENT = "If this is severe or sudden, press SOS or call 112 now."


def suggest(symptom: str) -> dict:
    s = symptom.lower()
    for keys, doctor, why, urgent in RULES:
        if any(k in s for k in keys):
            return {"doctor": doctor, "why": why, "urgent_note": URGENT if urgent else "", "disclaimer": DISCLAIMER}
    return {"doctor": "General Physician", "why": "A general physician is the best first stop for symptoms that are not clear.",
            "urgent_note": "", "disclaimer": DISCLAIMER}
