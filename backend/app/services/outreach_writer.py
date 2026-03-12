"""
Outreach Writer Service — Phase 3

Default mode: deterministic template-based generation (LLM_PROVIDER=template).
Extension point: set LLM_PROVIDER=openai and OPENAI_API_KEY to use GPT-backed generation.

IMPORTANT: This service ONLY generates content. It never sends emails.
"""

import json
import os
from typing import Optional, Tuple

from app.models.lead import Lead

LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "template")

_TONE_OPENERS = {
    "executive": "I'll be direct:",
    "professional": "I hope this message finds you well.",
    "casual": "Hey there!",
}

_SERVICE_DESCRIPTIONS = {
    "operations": "streamlining operations and reducing overhead",
    "strategy": "developing strategic growth plans and competitive positioning",
    "scaling": "accelerating growth and building scalable systems",
}

_SERVICE_SHORT = {
    "operations": "Operational Efficiency",
    "strategy": "Strategic Growth",
    "scaling": "Scaling Up",
}

_SERVICE_SHORT_LOWER = {
    "operations": "operational efficiency",
    "strategy": "strategic growth",
    "scaling": "scaling",
}


# ---------------------------------------------------------------------------
# Template helpers
# ---------------------------------------------------------------------------


def _template_subject(lead: Lead, tone: str, service_focus: str) -> str:
    service_label = _SERVICE_SHORT[service_focus]
    if tone == "executive":
        return f"Quick note for {lead.company_name} leadership — {service_label}"
    if tone == "casual":
        return f"{lead.company_name} + NorthStar: {service_label} ideas"
    return f"Helping {lead.company_name} with {service_label}"


def _template_body(
    lead: Lead,
    tone: str,
    service_focus: str,
    extra_context: Optional[str] = None,
) -> str:
    opener = _TONE_OPENERS[tone]
    service_desc = _SERVICE_DESCRIPTIONS[service_focus]
    company = lead.company_name
    industry = lead.industry or "your industry"
    extra = f"\n\nAdditional context: {extra_context}" if extra_context else ""

    if tone == "executive":
        return (
            f"{opener}\n\n"
            f"NorthStar Consulting specialises in {service_desc} for companies like {company}. "
            f"We have helped {industry} firms reduce costs and improve performance with measurable results.\n\n"
            f"I would like to schedule a 20-minute call to see if there is a fit.{extra}\n\n"
            "Best,\nThe NorthStar Team"
        )
    if tone == "casual":
        return (
            f"{opener}\n\n"
            f"I've been looking at {company} and think we could do some cool things together around {service_desc}. "
            f"NorthStar helps {industry} businesses like yours move faster and smarter.\n\n"
            f"Would love to chat — 15 minutes?{extra}\n\n"
            "Cheers,\nThe NorthStar Team"
        )
    # professional (default)
    return (
        f"{opener}\n\n"
        f"I'm reaching out because {company} caught our attention as a company doing interesting work in {industry}. "
        f"At NorthStar Consulting, we specialise in {service_desc} for businesses at your stage.\n\n"
        f"I'd welcome the opportunity to share how we've helped similar companies and explore whether we might be a good fit.{extra}\n\n"
        "Warm regards,\nThe NorthStar Team"
    )


def _template_followups(lead: Lead, tone: str, service_focus: str) -> Tuple[str, str, str]:
    company = lead.company_name
    service_label = _SERVICE_SHORT_LOWER[service_focus]

    followup_1 = (
        f"Hi again,\n\n"
        f"I wanted to follow up on my earlier message about helping {company} with {service_label}. "
        f"I know inboxes get busy — would a quick call this week work?\n\n"
        "Best,\nThe NorthStar Team"
    )

    followup_2 = (
        f"Hi,\n\n"
        f"Sharing a brief case study: we helped a company similar to {company} improve their {service_label} "
        f"by over 30% in 90 days. Happy to share details if helpful.\n\n"
        "Best,\nThe NorthStar Team"
    )

    followup_3 = (
        f"Hi,\n\n"
        f"I'll keep this short — if {company} isn't the right time or fit for our {service_label} work, "
        f"no worries at all. Just let me know and I won't follow up further. "
        f"If timing is better in a few months, I'm happy to reconnect then.\n\n"
        "Best,\nThe NorthStar Team"
    )

    return followup_1, followup_2, followup_3


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_outreach_message(
    lead: Lead,
    tone: str,
    service_focus: str,
    extra_context: Optional[str] = None,
) -> dict:
    """Generate a personalised outreach subject and body for *lead*.

    Returns a dict with keys ``subject`` and ``message``.
    Never sends email — content generation only.
    """
    if LLM_PROVIDER == "openai":
        return _openai_generate_message(lead, tone, service_focus, extra_context)
    return {
        "subject": _template_subject(lead, tone, service_focus),
        "message": _template_body(lead, tone, service_focus, extra_context),
    }


def generate_followups(lead: Lead, tone: str, service_focus: str) -> dict:
    """Generate a 3-step follow-up sequence for *lead*.

    Returns a dict with keys ``followup_1``, ``followup_2``, ``followup_3``.
    Never sends email — content generation only.
    """
    if LLM_PROVIDER == "openai":
        return _openai_generate_followups(lead, tone, service_focus)
    f1, f2, f3 = _template_followups(lead, tone, service_focus)
    return {"followup_1": f1, "followup_2": f2, "followup_3": f3}


# ---------------------------------------------------------------------------
# LLM extension point (requires LLM_PROVIDER=openai + OPENAI_API_KEY)
# ---------------------------------------------------------------------------


def _openai_generate_message(
    lead: Lead,
    tone: str,
    service_focus: str,
    extra_context: Optional[str],
) -> dict:
    """LLM-backed outreach message generation.  Falls back to templates on error."""
    try:
        import openai  # type: ignore

        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))
        prompt = (
            f"Write a cold outreach email for {lead.company_name} (industry: {lead.industry}). "
            f"Tone: {tone}. Service focus: {service_focus}. "
            f"Extra context: {extra_context or 'none'}. "
            "Return valid JSON with exactly two keys: 'subject' (string) and 'message' (string). "
            "Do not include any other text."
        )
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        result = json.loads(response.choices[0].message.content)
        return {"subject": str(result["subject"]), "message": str(result["message"])}
    except Exception:
        return {
            "subject": _template_subject(lead, tone, service_focus),
            "message": _template_body(lead, tone, service_focus, extra_context),
        }


def _openai_generate_followups(lead: Lead, tone: str, service_focus: str) -> dict:
    """LLM-backed follow-up generation.  Falls back to templates on error."""
    try:
        import openai  # type: ignore

        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))
        prompt = (
            f"Write 3 follow-up emails for {lead.company_name} (industry: {lead.industry}). "
            f"Tone: {tone}. Service focus: {service_focus}. "
            "Return valid JSON with exactly three keys: 'followup_1', 'followup_2', 'followup_3' (all strings). "
            "Do not include any other text."
        )
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        result = json.loads(response.choices[0].message.content)
        return {
            "followup_1": str(result["followup_1"]),
            "followup_2": str(result["followup_2"]),
            "followup_3": str(result["followup_3"]),
        }
    except Exception:
        f1, f2, f3 = _template_followups(lead, tone, service_focus)
        return {"followup_1": f1, "followup_2": f2, "followup_3": f3}
