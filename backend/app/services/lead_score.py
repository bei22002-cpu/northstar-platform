from typing import Optional


def score_lead(company_name: str, industry: Optional[str], website: Optional[str], email: Optional[str]) -> float:
    """
    Score a lead from 0.0 to 100.0 based on available data.
    Higher scores indicate more complete and valuable leads.
    """
    score = 0.0

    if company_name:
        score += 20.0

    if industry:
        score += 20.0
        high_value_industries = {"technology", "finance", "healthcare", "saas", "software"}
        if industry.lower() in high_value_industries:
            score += 15.0

    if website:
        score += 20.0

    if email:
        score += 25.0

    return min(score, 100.0)
