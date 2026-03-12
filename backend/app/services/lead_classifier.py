def classify_lead(score: float) -> str:
    """
    Classify a lead based on its numeric score.

    Classification tiers:
    - Hot:  score >= 75
    - Warm: score >= 45
    - Cold: score <  45
    """
    if score >= 75:
        return "hot"
    elif score >= 45:
        return "warm"
    else:
        return "cold"
