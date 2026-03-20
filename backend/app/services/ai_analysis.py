"""AI-powered business analysis service.

Uses OpenAI when OPENAI_API_KEY is configured, otherwise falls back to
rule-based mock analysis.
"""

import json
import logging
from typing import Optional

from app.core.config import OPENAI_API_KEY

logger = logging.getLogger(__name__)

_client = None


def _get_openai_client():
    """Lazy-init the OpenAI client so import never fails."""
    global _client
    if _client is None and OPENAI_API_KEY:
        from openai import OpenAI
        _client = OpenAI(api_key=OPENAI_API_KEY)
    return _client


# ── Industry knowledge base (used for fallback & prompt enrichment) ──────────

INDUSTRY_INSIGHTS = {
    "technology": {
        "market_trend": "Growing rapidly with AI/ML adoption",
        "competition_level": "High",
        "entry_barrier": "Medium-High",
        "key_success_factors": ["Innovation speed", "Technical talent", "Scalable architecture"],
    },
    "retail": {
        "market_trend": "Shifting to omnichannel and D2C models",
        "competition_level": "Very High",
        "entry_barrier": "Low-Medium",
        "key_success_factors": ["Customer experience", "Supply chain", "Brand building"],
    },
    "services": {
        "market_trend": "Increasing demand for specialized consulting",
        "competition_level": "Medium",
        "entry_barrier": "Low",
        "key_success_factors": ["Expertise", "Network", "Client relationships"],
    },
    "healthcare": {
        "market_trend": "Digital health and telehealth expansion",
        "competition_level": "Medium-High",
        "entry_barrier": "High",
        "key_success_factors": ["Regulatory compliance", "Clinical validation", "Trust"],
    },
    "finance": {
        "market_trend": "Fintech disruption and embedded finance",
        "competition_level": "High",
        "entry_barrier": "High",
        "key_success_factors": ["Regulatory navigation", "Security", "User trust"],
    },
    "education": {
        "market_trend": "EdTech growth with personalized learning",
        "competition_level": "Medium",
        "entry_barrier": "Medium",
        "key_success_factors": ["Content quality", "User engagement", "Accessibility"],
    },
}

DEFAULT_INSIGHT = {
    "market_trend": "Emerging opportunities available",
    "competition_level": "Varies",
    "entry_barrier": "Medium",
    "key_success_factors": ["Market research", "Execution speed", "Customer focus"],
}

FUNDING_STRATEGIES = [
    {
        "type": "bootstrapping",
        "description": "Self-fund initial development using personal savings or revenue",
        "suitability": "High for low-cost startups",
        "typical_amount": "$0 - $50,000",
    },
    {
        "type": "angel_investment",
        "description": "Seek funding from angel investors in your industry",
        "suitability": "Medium-High for tech startups",
        "typical_amount": "$25,000 - $500,000",
    },
    {
        "type": "crowdfunding",
        "description": "Launch a crowdfunding campaign to validate demand and raise funds",
        "suitability": "High for consumer products",
        "typical_amount": "$10,000 - $250,000",
    },
    {
        "type": "grants",
        "description": "Apply for government or private grants for innovation",
        "suitability": "Medium for technology companies",
        "typical_amount": "$10,000 - $2,000,000",
    },
    {
        "type": "venture_capital",
        "description": "Pitch to VC firms for larger funding rounds",
        "suitability": "High for scalable tech businesses",
        "typical_amount": "$500,000 - $10,000,000+",
    },
]


def _fallback_analysis(title: str, description: str, industry: str, target_market: Optional[str], budget_range: Optional[str]) -> dict:
    """Rule-based analysis when OpenAI is not available."""
    base_insight = INDUSTRY_INSIGHTS.get(industry, DEFAULT_INSIGHT)
    return {
        "industry_analysis": base_insight,
        "recommended_next_steps": [
            "Validate the idea with potential customers",
            "Build a minimum viable product (MVP)",
            "Identify key competitors and differentiators",
            "Develop a go-to-market strategy",
            "Secure initial funding or bootstrap",
        ],
        "risk_factors": [
            "Market timing and readiness",
            "Funding availability",
            "Team capability gaps",
            "Regulatory requirements",
        ],
        "estimated_timeline": "3-6 months to MVP, 12-18 months to market fit",
    }


def _fallback_funding(budget_range: Optional[str]) -> dict:
    """Rule-based funding strategy when OpenAI is not available."""
    primary = FUNDING_STRATEGIES[0]["type"] if budget_range in [None, "", "0-10k"] else FUNDING_STRATEGIES[1]["type"]
    return {
        "recommended_strategies": FUNDING_STRATEGIES,
        "primary_recommendation": primary,
        "funding_readiness_checklist": [
            "Business plan or pitch deck prepared",
            "Market research completed",
            "MVP or prototype available",
            "Financial projections ready",
            "Team assembled or identified",
        ],
    }


def generate_analysis(title: str, description: str, industry: str, target_market: Optional[str] = None, budget_range: Optional[str] = None) -> dict:
    """Generate AI-powered business analysis.

    Uses OpenAI GPT when API key is configured, otherwise returns rule-based analysis.
    """
    client = _get_openai_client()
    if client is None:
        logger.info("OpenAI not configured — using fallback analysis")
        return _fallback_analysis(title, description, industry, target_market, budget_range)

    prompt = f"""Analyze this business idea and return a JSON object with the following structure:
{{
  "industry_analysis": {{
    "market_trend": "...",
    "competition_level": "...",
    "entry_barrier": "...",
    "key_success_factors": ["...", "..."]
  }},
  "recommended_next_steps": ["step1", "step2", ...],
  "risk_factors": ["risk1", "risk2", ...],
  "estimated_timeline": "..."
}}

Business Idea:
- Title: {title}
- Description: {description}
- Industry: {industry}
- Target Market: {target_market or 'General'}
- Budget Range: {budget_range or 'Not specified'}

Provide actionable, specific insights. Return ONLY valid JSON."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert business analyst. Always respond with valid JSON only."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=1000,
        )
        content = response.choices[0].message.content.strip()
        # Strip markdown code fences if present
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        return json.loads(content)
    except Exception as e:
        logger.warning("OpenAI analysis failed, using fallback: %s", e)
        return _fallback_analysis(title, description, industry, target_market, budget_range)


def suggest_funding(title: str, description: str, industry: str, target_market: Optional[str] = None, budget_range: Optional[str] = None) -> dict:
    """Generate AI-powered funding strategy recommendations.

    Uses OpenAI GPT when API key is configured, otherwise returns rule-based strategies.
    """
    client = _get_openai_client()
    if client is None:
        logger.info("OpenAI not configured — using fallback funding strategy")
        return _fallback_funding(budget_range)

    prompt = f"""Recommend funding strategies for this business idea and return a JSON object:
{{
  "recommended_strategies": [
    {{"type": "...", "description": "...", "suitability": "...", "typical_amount": "..."}}
  ],
  "primary_recommendation": "strategy_type",
  "funding_readiness_checklist": ["item1", "item2", ...]
}}

Business Idea:
- Title: {title}
- Description: {description}
- Industry: {industry}
- Target Market: {target_market or 'General'}
- Budget Range: {budget_range or 'Not specified'}

Include 4-6 strategies ranked by suitability. Return ONLY valid JSON."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert startup funding advisor. Always respond with valid JSON only."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=1000,
        )
        content = response.choices[0].message.content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        return json.loads(content)
    except Exception as e:
        logger.warning("OpenAI funding strategy failed, using fallback: %s", e)
        return _fallback_funding(budget_range)
