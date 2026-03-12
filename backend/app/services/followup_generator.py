from typing import Optional


_FOLLOWUP_TEMPLATES = {
    1: {
        "subject": "Following up — {company}",
        "body": (
            "Hi {contact},\n\n"
            "I wanted to follow up on my previous message about NorthStar. "
            "I know your schedule is busy, so I'll keep this brief.\n\n"
            "We've helped similar companies accelerate their pipeline with AI-powered lead insights. "
            "Would a short call work for you this week?\n\n"
            "Best,\n"
            "The NorthStar Team"
        ),
    },
    2: {
        "subject": "Last follow-up — NorthStar + {company}",
        "body": (
            "Hi {contact},\n\n"
            "I'll keep this as my last follow-up — I don't want to crowd your inbox.\n\n"
            "If the timing isn't right, no worries at all. Feel free to reach back out whenever "
            "it makes sense for you.\n\n"
            "Wishing you and the {company} team all the best!\n\n"
            "The NorthStar Team"
        ),
    },
}

_DEFAULT_FOLLOWUP = {
    "subject": "Checking in — {company}",
    "body": (
        "Hi {contact},\n\n"
        "Just checking in to see if you had a chance to review my earlier message about NorthStar.\n\n"
        "Happy to answer any questions or share more details whenever works for you.\n\n"
        "Best,\n"
        "The NorthStar Team"
    ),
}


def generate_followup(
    company_name: str,
    contact_name: Optional[str],
    sequence_number: int = 1,
) -> dict:
    """
    Generate a follow-up message for a given outreach sequence position.

    Args:
        company_name: The lead's company name.
        contact_name: The lead's contact person name (optional).
        sequence_number: Position in the follow-up sequence (1, 2, ...).

    Returns:
        A dict with 'subject' and 'body' keys.
    """
    template = _FOLLOWUP_TEMPLATES.get(sequence_number, _DEFAULT_FOLLOWUP)
    contact = contact_name or "there"
    return {
        "subject": template["subject"].format(company=company_name, contact=contact),
        "body": template["body"].format(company=company_name, contact=contact),
    }
