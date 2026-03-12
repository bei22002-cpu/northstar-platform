"""
Unit tests for the outreach_writer service.

These tests are fully standalone — no database, no HTTP, no external services.
They verify that the template-based generation produces correctly-shaped output.
"""

from unittest.mock import MagicMock

import pytest

from app.services.outreach_writer import generate_followups, generate_outreach_message


def make_lead(company_name: str = "Acme Corp", industry: str = "Technology"):
    """Return a mock Lead object with the given attributes."""
    lead = MagicMock()
    lead.company_name = company_name
    lead.industry = industry
    lead.website = "https://example.com"
    lead.description = "A sample company"
    lead.score = 85.0
    return lead


# ---------------------------------------------------------------------------
# generate_outreach_message
# ---------------------------------------------------------------------------


class TestGenerateOutreachMessage:
    def test_returns_subject_and_message_keys(self):
        result = generate_outreach_message(make_lead(), "professional", "operations")
        assert "subject" in result
        assert "message" in result

    def test_subject_and_message_are_non_empty_strings(self):
        result = generate_outreach_message(make_lead(), "professional", "operations")
        assert isinstance(result["subject"], str) and result["subject"]
        assert isinstance(result["message"], str) and result["message"]

    def test_company_name_in_subject(self):
        result = generate_outreach_message(make_lead("TechCorp Inc"), "professional", "operations")
        assert "TechCorp Inc" in result["subject"]

    def test_executive_tone_opener(self):
        result = generate_outreach_message(make_lead(), "executive", "strategy")
        assert "I'll be direct" in result["message"]

    def test_casual_tone_opener(self):
        result = generate_outreach_message(make_lead(), "casual", "scaling")
        assert "Hey there" in result["message"]

    def test_professional_tone_opener(self):
        result = generate_outreach_message(make_lead(), "professional", "operations")
        assert "I hope this message finds you well" in result["message"]

    def test_extra_context_included_in_message(self):
        result = generate_outreach_message(
            make_lead(), "professional", "operations", extra_context="They just raised $10M"
        )
        assert "They just raised $10M" in result["message"]

    def test_extra_context_none_does_not_appear_as_none_string(self):
        result = generate_outreach_message(make_lead(), "professional", "operations", extra_context=None)
        assert "None" not in result["message"]

    def test_industry_in_message(self):
        result = generate_outreach_message(make_lead(industry="Retail"), "professional", "operations")
        assert "Retail" in result["message"]

    @pytest.mark.parametrize("tone", ["executive", "professional", "casual"])
    @pytest.mark.parametrize("focus", ["operations", "strategy", "scaling"])
    def test_all_tone_and_focus_combinations_produce_output(self, tone, focus):
        result = generate_outreach_message(make_lead(), tone, focus)
        assert result["subject"]
        assert result["message"]


# ---------------------------------------------------------------------------
# generate_followups
# ---------------------------------------------------------------------------


class TestGenerateFollowups:
    def test_returns_three_followup_keys(self):
        result = generate_followups(make_lead(), "professional", "operations")
        assert "followup_1" in result
        assert "followup_2" in result
        assert "followup_3" in result

    def test_all_followups_are_non_empty_strings(self):
        result = generate_followups(make_lead(), "professional", "operations")
        assert isinstance(result["followup_1"], str) and result["followup_1"]
        assert isinstance(result["followup_2"], str) and result["followup_2"]
        assert isinstance(result["followup_3"], str) and result["followup_3"]

    def test_company_name_appears_in_followups(self):
        result = generate_followups(make_lead("GlobalRetail"), "professional", "scaling")
        combined = result["followup_1"] + result["followup_2"] + result["followup_3"]
        assert "GlobalRetail" in combined

    def test_followups_differ_from_each_other(self):
        result = generate_followups(make_lead(), "professional", "operations")
        assert result["followup_1"] != result["followup_2"]
        assert result["followup_2"] != result["followup_3"]

    @pytest.mark.parametrize("tone", ["executive", "professional", "casual"])
    @pytest.mark.parametrize("focus", ["operations", "strategy", "scaling"])
    def test_all_combinations_produce_output(self, tone, focus):
        result = generate_followups(make_lead(), tone, focus)
        assert result["followup_1"] and result["followup_2"] and result["followup_3"]
