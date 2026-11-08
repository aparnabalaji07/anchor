def score_household(h: dict) -> tuple[int, list[str]]:
    """Returns (score, reasons). Higher score = call sooner."""
    score = 0
    reasons = []

    # A home that is dark right now outranks one whose outage already ended
    if h.get("out_now"):
        score += 40
        reasons.append("Power is out right now")

    hours = h["outage_hours"]
    if hours > 0:
        score += int(min(hours, 20) * 2) 
        reasons.append(f"Power out {hours:.1f} hours")

    t = h["min_temp"]
    if t is not None:
        if t < 40:
            score += 25
            reasons.append(f"House dropped to {t:.0f}°F, pipes may freeze")
        elif t < 50:
            score += 15
            reasons.append(f"House dropped to {t:.0f}°F")
        elif t < 60:
            score += 5

    if h["medical_device"]:
        score += 15
        reasons.append("Uses a medical device")
    if h["lives_alone"]:
        score += 10
        reasons.append("Lives alone")
    if h["mobility_limits"]:
        score += 10
        reasons.append("Mobility limits")
    if h["call_requested"]:
        score += 15
        reasons.append("Asked for a call")

    if not reasons:
        reasons.append("Short or no outage, probably fine")

    return score, reasons