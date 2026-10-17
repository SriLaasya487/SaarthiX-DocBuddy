"""Default flag ranges are placeholders. Production should use doctor-set ranges per elder."""
def is_flagged(kind: str, v1: float, v2: float | None) -> bool:
    if kind == "bp":
        return v1 >= 140 or v1 < 90 or (v2 or 0) >= 90 or (v2 is not None and v2 < 60)
    if kind == "sugar":
        return v1 >= 180 or v1 < 70
    if kind == "spo2":
        return v1 < 94
    if kind == "pulse":
        return v1 > 110 or v1 < 50
    return False
