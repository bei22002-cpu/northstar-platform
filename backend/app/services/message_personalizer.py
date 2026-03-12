from typing import Optional


_TEMPLATES = {
    "executive": {
        "subject": "Strategic Partnership Opportunity — {company}",
        "body": (
            "Dear {contact},\n\n"
            "I hope this message finds you well. I am reaching out regarding a strategic opportunity "
            "that I believe aligns with {company}'s goals.\n\n"
            "Our platform, NorthStar, helps organizations like yours identify high-value opportunities "
            "through AI-powered intelligence. I would welcome the chance to connect at your earliest "
            "convenience to discuss how we can create mutual value.\n\n"
            "Best regards,\n"
            "The NorthStar Team"
        ),
    },
    "professional": {
        "subject": "Introducing NorthStar — AI-Powered Lead Intelligence for {company}",
        "body": (
            "Hi {contact},\n\n"
            "I wanted to reach out and introduce NorthStar, an AI-powered platform that helps "
            "businesses like {company} streamline lead generation and outreach.\n\n"
            "We specialize in turning publicly available market data into actionable insights, "
            "so your team can focus on closing deals rather than searching for them.\n\n"
            "Would you be open to a quick 15-minute call this week?\n\n"
            "Thanks,\n"
            "The NorthStar Team"
        ),
    },
    "casual": {
        "subject": "Hey {contact} — quick question about {company}",
        "body": (
            "Hey {contact},\n\n"
            "I came across {company} and thought you might be interested in what we're building "
            "at NorthStar — it's an AI tool that makes finding and reaching the right leads "
            "way easier.\n\n"
            "Would love to show you a quick demo if you're curious!\n\n"
            "Cheers,\n"
            "The NorthStar Team"
        ),
    },
}


def personalize_message(
    company_name: str,
    contact_name: Optional[str],
    tone: str = "professional",
) -> dict:
    """
    Generate a personalized outreach message for a lead.

    Args:
        company_name: The lead's company name.
        contact_name: The lead's contact person name (optional).
        tone: One of 'executive', 'professional', or 'casual'.

    Returns:
        A dict with 'subject' and 'body' keys.
    """
    template = _TEMPLATES.get(tone, _TEMPLATES["professional"])
    contact = contact_name or "there"
    return {
        "subject": template["subject"].format(company=company_name, contact=contact),
        "body": template["body"].format(company=company_name, contact=contact),
    }
