def classify_lead(score: float) -> str:
    """
    Classify a lead based on its score.

    Returns:
        'hot'  — score >= 75
        'warm' — score >= 45
        'cold' — score < 45
    """
    if score >= 75:
        return "hot"
    elif score >= 45:
        return "warm"
    return "cold"
