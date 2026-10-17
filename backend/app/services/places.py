"""Nearest hospital/pharmacy (OpenStreetMap Overpass) and weather/air (Open-Meteo). Network failures degrade to map links."""
import math
import re

import httpx

OVERPASS = "https://overpass-api.de/api/interpreter"


def haversine_km(a, b, c, d) -> float:
    p = math.pi / 180
    x = math.sin((c - a) * p / 2) ** 2 + math.cos(a * p) * math.cos(c * p) * math.sin((d - b) * p / 2) ** 2
    return 12742 * math.asin(math.sqrt(x))


def open_late(hours: str) -> bool:
    if not hours:
        return False
    if "24/7" in hours:
        return True
    ends = [int(h) for h, _ in re.findall(r"-\s*(\d{2}):(\d{2})", hours)]
    return any(e >= 22 or e <= 5 for e in ends)


def find(kind: str, lat: float, lng: float, radius_m: int = 5000, only_late: bool = False, fetch=None) -> dict:
    tag = "hospital" if kind == "hospital" else "pharmacy"
    q = f'[out:json][timeout:15];(node["amenity"="{tag}"](around:{radius_m},{lat},{lng});way["amenity"="{tag}"](around:{radius_m},{lat},{lng}););out center 30;'
    maps = f"https://www.google.com/maps/search/{tag}+open+now/@{lat},{lng},14z"
    try:
        data = (fetch or (lambda q: httpx.post(OVERPASS, data={"data": q}, timeout=20).json()))(q)
    except Exception:
        return {"places": [], "maps_link": maps, "note": "Could not reach the map service. Use the map link or call 112 / 108."}
    out = []
    for e in data.get("elements", []):
        t = e.get("tags", {})
        la, lo = e.get("lat") or e.get("center", {}).get("lat"), e.get("lon") or e.get("center", {}).get("lon")
        if la is None:
            continue
        late = open_late(t.get("opening_hours", ""))
        if only_late and not late:
            continue
        phone = (t.get("phone") or t.get("contact:phone") or "").split(";")[0].strip()
        out.append({"name": t.get("name", tag.title()), "km": round(haversine_km(lat, lng, la, lo), 1), "open_late": late, "hours": t.get("opening_hours", ""),
                    "phone": phone, "call": f"tel:{phone}" if phone else "", "directions": f"https://www.google.com/maps/dir/?api=1&destination={la},{lo}"})
    out.sort(key=lambda p: p["km"])
    return {"places": out[:10], "maps_link": maps, "note": "Opening hours come from volunteers and may be wrong - call before you go."}


def weather(lat: float, lng: float, fetch=None) -> dict:
    try:
        get = fetch or (lambda u, p: httpx.get(u, params=p, timeout=10).json())
        w = get("https://api.open-meteo.com/v1/forecast", {"latitude": lat, "longitude": lng, "current": "temperature_2m", "daily": "temperature_2m_max,temperature_2m_min", "timezone": "auto"})
        a = get("https://air-quality-api.open-meteo.com/v1/air-quality", {"latitude": lat, "longitude": lng, "current": "us_aqi"})
        return {"temp_c": w["current"]["temperature_2m"], "max_c": w["daily"]["temperature_2m_max"][0], "aqi": a.get("current", {}).get("us_aqi")}
    except Exception:
        return {"temp_c": None, "max_c": None, "aqi": None}
