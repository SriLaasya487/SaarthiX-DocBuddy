"""Static, reviewable content. Everything here is INFORMATION ONLY - nothing diagnoses or prescribes.
Items marked verify=True change over time; have a person re-check them before each release."""

HELPLINES = [
    {"name": "National emergency", "number": "112", "kind": "emergency"},
    {"name": "Ambulance", "number": "108", "kind": "emergency", "verify": True},
    {"name": "Police", "number": "100", "kind": "emergency"},
    {"name": "Fire", "number": "101", "kind": "emergency"},
    {"name": "Elderline (senior citizens)", "number": "14567", "kind": "elder"},
    {"name": "Cyber-crime helpline", "number": "1930", "kind": "scam"},
    {"name": "Tele-MANAS (mental health)", "number": "14416", "kind": "wellbeing", "verify": True},
    {"name": "Disaster management", "number": "1078", "kind": "disaster", "verify": True},
    {"name": "Women helpline", "number": "181", "kind": "other"},
]

BREATHING = {"name": "Slow breathing", "pattern": {"in": 4, "hold": 2, "out": 6}, "rounds": 6,
             "script": ["Sit comfortably.", "Breathe in slowly through your nose.", "Hold gently.", "Breathe out slowly through your mouth."]}

ANXIETY_STEPS = [
    "You are safe right now. Let us go slowly, one step at a time.",
    "Sit down if you can. Put both feet on the floor.",
    "Breathe in slowly... and breathe out slowly. Do this three times.",
    "Look around. Name five things you can see.",
    "Now touch something near you. Feel it. Name four things you can touch.",
    "Listen. What are two sounds you can hear?",
    "Drink a few sips of water.",
    "Would you like me to call someone you trust, or tell your family? You choose.",
]

HOME_SAFETY = [
    ("floors", "Floors are dry and free of loose rugs or wires"), ("lights", "Bathroom, bedroom and passage have night lights"),
    ("grab_bars", "Grab bars near the toilet and shower"), ("stair_rails", "Sturdy handrails on both sides of the stairs"),
    ("footwear", "Non-slip chappals or shoes are used indoors"), ("bathroom_mat", "Anti-slip mat in the bathroom"),
    ("phone", "Phone and torch are within reach of the bed"), ("meds_store", "Medicines are stored in one labelled place"),
    ("gas", "Gas stove has auto cut-off or is checked at night"), ("numbers", "Emergency numbers are written large near the phone"),
]

LESSONS = [
    {"id": "videocall", "title": "Making a video call", "steps": ["Open the DocBuddy home screen.", "Tap the green Call button.", "Wait for your family member's face.", "Tap the red button to end."],
     "quiz": [{"q": "Which button ends the call?", "options": ["Green", "Red"], "answer": 1}]},
    {"id": "banksms", "title": "Reading a bank SMS safely", "steps": ["A real bank SMS shows money moved or a balance. It never asks you to do something.", "Never share the OTP with anyone - not even the bank.", "Do not tap links in SMS. Go to the bank app yourself.", "If unsure, show it to DocBuddy's Scam Check."],
     "quiz": [{"q": "A caller from the 'bank' asks for your OTP. What do you do?", "options": ["Give it", "Hang up"], "answer": 1}]},
    {"id": "upi", "title": "Paying with UPI safely", "steps": ["You only enter your PIN to SEND money, never to RECEIVE.", "Check the name on the screen before paying.", "Never scan a QR code to 'receive' money."],
     "quiz": [{"q": "To receive money you must enter your PIN.", "options": ["True", "False"], "answer": 1}]},
    {"id": "fakelinks", "title": "Spotting fake links and lottery messages", "steps": ["You cannot win a lottery you never entered.", "Urgent words like 'today only' or 'account blocked' are warning signs.", "Ask your family before clicking."],
     "quiz": [{"q": "'You won Rs 25 lakh! Click now.' is...", "options": ["Real", "A scam"], "answer": 1}]},
    {"id": "voice", "title": "Talking to DocBuddy", "steps": ["Tap the microphone.", "Speak slowly, in your language.", "Tap 'Hear again' or 'Slow down' any time."],
     "quiz": [{"q": "Which button repeats what DocBuddy said?", "options": ["Hear again", "Sign out"], "answer": 0}]},
]

SAFE_CHECK_STEPS = {  # insurance claim steps (general; confirm with your insurer)
    "claim": ["Call the insurer / TPA helpline from the policy card and give the policy number.", "For planned admission, ask for pre-authorisation 2-3 days earlier.",
              "Keep all bills, discharge summary, prescriptions and reports.", "Submit the claim form with documents within the time limit in your policy.", "Note the claim number and follow up in writing."],
}

VACCINES = [  # general adult schedule shown for DISCUSSION with a doctor
    {"id": "flu", "name": "Influenza (flu)", "every_months": 12, "note": "Usually once every year before the season."},
    {"id": "pneumo", "name": "Pneumococcal", "every_months": None, "note": "Ask your doctor if you need it and which type."},
    {"id": "shingles", "name": "Shingles (herpes zoster)", "every_months": None, "note": "Often 2 doses. Ask your doctor."},
    {"id": "td", "name": "Tetanus (Td/Tdap) booster", "every_months": 120, "note": "Usually every 10 years or after a deep wound."},
    {"id": "covid", "name": "COVID-19", "every_months": 12, "note": "Follow current national guidance and your doctor.", "verify": True},
]
CHECKUPS = [
    {"id": "eyes", "name": "Eye check", "every_months": 12}, {"id": "hearing", "name": "Hearing check", "every_months": 12},
    {"id": "dental", "name": "Dental check", "every_months": 6}, {"id": "bone", "name": "Bone density", "every_months": 24, "note": "Ask your doctor if you need it."},
    {"id": "lipid", "name": "Cholesterol", "every_months": 12}, {"id": "sugar", "name": "HbA1c / sugar", "every_months": 6},
    {"id": "bp", "name": "Blood pressure review", "every_months": 6}, {"id": "kidney", "name": "Kidney function", "every_months": 12},
]

FESTIVALS_FIXED = {"01-14": "Makar Sankranti / Pongal", "01-26": "Republic Day", "04-14": "Baisakhi", "08-15": "Independence Day",
                   "10-02": "Gandhi Jayanti", "12-25": "Christmas"}
FESTIVALS_2026 = {  # lunar-calendar dates move every year; verify=True, refresh annually
    "2026-03-04": "Holi", "2026-03-20": "Eid al-Fitr", "2026-08-28": "Raksha Bandhan", "2026-09-14": "Ganesh Chaturthi",
    "2026-10-20": "Dussehra", "2026-11-08": "Diwali", "2026-11-24": "Guru Nanak Jayanti"}
GREETING = {"hi": "{f} की हार्दिक शुभकामनाएँ!", "te": "{f} శుభాకాంక్షలు!", "ta": "{f} நல்வாழ்த்துக்கள்!", "bn": "{f}-এর শুভেচ্ছা!",
            "mr": "{f} च्या हार्दिक शुभेच्छा!", "kn": "{f} ಶುಭಾಶಯಗಳು!", "gu": "{f} ની શુભેચ્છાઓ!", "en": "Happy {f}!"}
BIRTHDAY = {"hi": "{n} को जन्मदिन की शुभकामनाएँ!", "te": "{n} కు పుట్టినరోజు శుభాకాంక్షలు!", "ta": "{n} க்கு பிறந்தநாள் வாழ்த்துக்கள்!",
            "en": "Happy birthday, {n}!"}

DEVOTIONAL = {  # curated SEARCH queries - no copyrighted audio is bundled
    "hindu": ["morning bhajan", "hanuman chalisa", "aarti", "vishnu sahasranamam", "kirtan"],
    "sikh": ["nitnem path", "japji sahib", "shabad kirtan", "gurbani"],
    "muslim": ["quran recitation", "naat", "dua morning"],
    "christian": ["hymns", "christian worship songs", "rosary prayer"],
    "buddhist": ["buddhist chanting", "metta meditation"], "jain": ["navkar mantra", "jain stavan"],
}

SCHEMES = [  # EDITABLE catalogue. Eligibility is indicative: always confirm on the official site / local office.
    {"id": "vay_vandana", "name": "Ayushman Vay Vandana card (PM-JAY, 70+)", "min_age": 70, "docs": ["Aadhaar", "Mobile number"], "where": "pmjay.gov.in", "verify": True,
     "why": "Health cover for senior citizens aged 70 and above."},
    {"id": "pmjay", "name": "Ayushman Bharat PM-JAY", "min_age": 0, "income": "low", "docs": ["Aadhaar", "Ration card"], "where": "pmjay.gov.in", "verify": True,
     "why": "Hospital cover for eligible low-income households."},
    {"id": "ignoaps", "name": "Indira Gandhi National Old Age Pension (IGNOAPS)", "min_age": 60, "income": "bpl", "docs": ["Aadhaar", "Age proof", "BPL proof", "Bank passbook"], "where": "nsap.nic.in / state social welfare dept", "verify": True,
     "why": "Monthly pension for senior citizens below the poverty line."},
    {"id": "scss", "name": "Senior Citizens Savings Scheme (SCSS)", "min_age": 60, "docs": ["Aadhaar", "PAN", "Age proof"], "where": "Post office / designated banks", "verify": True,
     "why": "Savings scheme with regular interest for people aged 60+."},
    {"id": "jeevan_pramaan", "name": "Jeevan Pramaan (digital life certificate)", "min_age": 0, "pensioner": True, "docs": ["Aadhaar", "Pension details"], "where": "jeevanpramaan.gov.in", "verify": True,
     "why": "Pensioners can submit their life certificate without visiting the office."},
    {"id": "tax", "name": "Income-tax benefits for senior citizens", "min_age": 60, "docs": ["PAN"], "where": "incometax.gov.in", "verify": True,
     "why": "Higher exemption limits and interest deductions for 60+/80+. Ask a tax advisor."},
    {"id": "rail", "name": "Railway senior-citizen concession", "min_age": 58, "docs": ["Age proof"], "where": "indianrailways.gov.in", "verify": True,
     "why": "A concession existed for 58+/60+; its current status changes - check before travel."},
]

GAMES = {
    "pairs": {"name": "Match the pairs", "levels": [3, 4, 5, 6, 8, 10]},
    "sequence": {"name": "Repeat the pattern", "levels": [3, 4, 5, 6, 7, 8]},
    "words": {"name": "Remember the words", "levels": [3, 4, 5, 6, 7, 8]},
}
WORDS = ["apple", "table", "river", "mango", "lamp", "garden", "temple", "pencil", "window", "tiger", "blanket", "coconut", "mirror", "train", "flower", "bicycle"]

TRANSPORT = {"railway": "https://www.irctc.co.in", "maps": "https://www.google.com/maps/dir/?api=1&destination="}

COMMUNITY_SEED = [("Morning satsang", "", "devotional"), ("Bhajan circle", "", "music"), ("Morning walkers", "", "walking"),
                  ("Grandparents' stories", "", "stories"), ("Chess and carrom", "", "games")]
BANNED = ("sex", "kill", "idiot", "stupid", "bet ", "lottery", "invest", "send money", "whatsapp me", "click here", "http://", "https://")

NEWS_FEEDS = {"en": "https://feeds.bbci.co.uk/news/world/asia/india/rss.xml", "hi": "https://feeds.bbci.co.uk/hindi/rss.xml",
              "ta": "https://feeds.bbci.co.uk/tamil/rss.xml", "te": "https://feeds.bbci.co.uk/telugu/rss.xml",
              "mr": "https://feeds.bbci.co.uk/marathi/rss.xml", "bn": "https://feeds.bbci.co.uk/bengali/rss.xml",
              "gu": "https://feeds.bbci.co.uk/gujarati/rss.xml"}
