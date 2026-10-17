"""Voice assistant for small tasks + AI companion. The assistant NEVER pays, calls or sends on its own:
it returns an ACTION the app shows and the elder confirms."""
import re
from datetime import datetime, timedelta

import httpx

from ..config import settings
from . import content as K

SYSTEM = ("You are DocBuddy, a warm, patient companion for an elderly person in India. Speak in short, simple sentences in the user's language. "
          "NEVER diagnose, never recommend medicines or doses, never ask for OTPs, money or passwords. For anything medical say: please ask your doctor. "
          "If the person seems in danger or very sad, gently suggest pressing SOS or telling family. Keep replies under 60 words.")

SMALLTALK = [(r"\b(hello|hi|namaste|namaskar|vanakkam)\b", "Namaste! It is lovely to hear from you. How is your day going?"),
             (r"how are you", "I am well, thank you for asking. How are you feeling today?"),
             (r"\b(lonely|alone|bored)\b", "I am here with you. Would you like some music, a story, or shall I help you call someone?"),
             (r"\b(story|kahani)\b", "Once a small sparrow shared her last grain with a hungry crow. The next winter, the crow led her to a warm barn. Kindness always finds its way home."),
             (r"\b(joke)\b", "Why did the tomato blush? Because it saw the salad dressing!"),
             (r"\b(thank)", "You are most welcome.")]


def chat(text: str, history: list[dict] | None = None) -> dict:
    if settings.llm_api_key:
        try:
            msgs = (history or [])[-8:] + [{"role": "user", "content": text}]
            r = httpx.post("https://api.anthropic.com/v1/messages", timeout=20,
                           headers={"x-api-key": settings.llm_api_key, "anthropic-version": "2023-06-01"},
                           json={"model": settings.llm_model, "max_tokens": 200, "system": SYSTEM, "messages": msgs})
            if r.is_success:
                return {"reply": r.json()["content"][0]["text"], "engine": "llm"}
        except (httpx.HTTPError, KeyError, IndexError):
            pass
    low = text.lower()
    if re.search(r"\b(pain|chest|breath|dizzy|bleed|faint|fell|fall)\b", low):
        return {"reply": "That sounds important. Please tell your doctor. If it is severe or sudden, press SOS or call 112 now.", "engine": "rules"}
    for pat, reply in SMALLTALK:
        if re.search(pat, low):
            return {"reply": reply, "engine": "rules"}
    return {"reply": "I am listening. Tell me more, or ask me to play music, read the news, or call someone.", "engine": "rules"}


def intent(text: str, contacts: list[dict] | None = None) -> dict:
    low = text.lower().strip()
    contacts = contacts or []
    m = re.search(r"\b(?:call|phone|dial|ring)\s+(?:my\s+)?([a-z ]+)", low)
    if m:
        who = m.group(1).strip()
        c = next((c for c in contacts if c["name"].lower() in who or who in c["name"].lower() or (c.get("relation") and c["relation"] in who)), None)
        return {"intent": "call", "speak": f"Calling {c['name']}. Say yes to confirm." if c else f"I could not find {who} in your contacts.",
                "action": {"type": "tel", "href": f"tel:{c['phone']}", "needs_confirm": True} if c else None}
    if re.search(r"\b(read|open)\b.*\b(message|messages|sms)\b", low):
        return {"intent": "read_messages", "speak": "Reading your latest messages.", "action": {"type": "ui", "route": "messages"}}
    m = re.search(r"(?:alarm|wake me|remind me)(?:.*?\bat\b)?\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", low)
    if m or re.search(r"\b(set|make)\b.*\balarm\b", low):
        if m:
            h, mi, ap = int(m.group(1)), int(m.group(2) or 0), m.group(3)
            if ap == "pm" and h < 12: h += 12
            if ap == "am" and h == 12: h = 0
            return {"intent": "alarm", "speak": f"Alarm for {h:02d}:{mi:02d}. Say yes to set it.", "action": {"type": "alarm", "time": f"{h:02d}:{mi:02d}", "needs_confirm": True}}
        return {"intent": "alarm", "speak": "For what time should I set the alarm?", "action": None}
    m = re.search(r"(?:bus|train|route|go|way)\s+(?:to|for)\s+([a-z ]+)", low)
    if m or re.search(r"\b(train|bus|ticket)\b", low):
        dest = (m.group(1).strip() if m else "")
        url = (K.TRANSPORT["maps"] + dest.replace(" ", "+") + "&travelmode=transit") if dest else K.TRANSPORT["railway"]
        return {"intent": "transport", "speak": f"I will show transport options{' to ' + dest if dest else ''}.", "action": {"type": "link", "href": url}}
    m = re.search(r"pay\s+(?:my\s+)?([a-z ]+?)\s*(?:bill)?(?:\s+of\s+(?:rs\.?\s*)?(\d+))?$", low)
    if re.search(r"\bpay\b.*\bbill\b|\bbill\b.*\bpay\b", low):
        return {"intent": "pay_bill", "speak": "I will open your payment app. You must check the amount and enter your own PIN. I never pay for you.",
                "action": {"type": "link", "href": "upi://pay", "needs_confirm": True, "never_automatic": True}}
    if re.search(r"\b(news|akhbar|headlines)\b", low):
        return {"intent": "news", "speak": "Here are today's headlines.", "action": {"type": "ui", "route": "news"}}
    if re.search(r"\b(music|song|bhajan|gana)\b", low):
        return {"intent": "music", "speak": "Opening music.", "action": {"type": "ui", "route": "companion"}}
    if re.search(r"\b(medicine|tablet|dawai|dawa)\b", low):
        return {"intent": "medicines", "speak": "Opening your medicines.", "action": {"type": "ui", "route": "meds"}}
    if re.search(r"\b(help|sos|emergency|bachao)\b", low):
        return {"intent": "sos", "speak": "Say yes to send an emergency alert.", "action": {"type": "sos", "needs_confirm": True}}
    if re.search(r"\b(i am fine|i'm fine|main theek)\b", low):
        return {"intent": "imfine", "speak": "Shall I tell your family that you are fine?", "action": {"type": "imfine", "needs_confirm": True}}
    if re.search(r"\b(who saw|who has seen|kisne dekha)\b", low):
        return {"intent": "audit", "speak": "Let me read who saw your information.", "action": {"type": "ui", "route": "sharing"}}
    return {"intent": "chat", "speak": "", "action": None}
