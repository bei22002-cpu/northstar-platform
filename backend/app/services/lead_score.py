def score_lead(lead_data: dict) -> float:
    """
    Score a lead on a 0–100 scale based on available data quality signals.

    Signals considered:
    - Has a company website (+20)
    - Has a contact email (+20)
    - Has a contact name (+15)
    - Has a known industry (+15)
    - Has notes/context (+10)
    - Company name length heuristic (longer = more descriptive, up to +20)
    """
    score = 0.0

    if lead_data.get("website"):
        score += 20
    if lead_data.get("email"):
        score += 20
    if lead_data.get("contact_name"):
        score += 15
    if lead_data.get("industry"):
        score += 15
    if lead_data.get("notes"):
        score += 10

    company_name = lead_data.get("company_name", "")
    name_score = min(len(company_name) / 50.0, 1.0) * 20
    score += name_score

    return round(min(score, 100.0), 2)
