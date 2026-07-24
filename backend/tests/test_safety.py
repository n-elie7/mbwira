"""Tests for the crisis-detection safety layer, with different scenarios like languages and edge cases."""


import pytest

from app.services.safety import (
    check_user_message,
    extract_escalation_from_response,
    safety_response_text,
)

class TestCheckUserMessage:
    def test_empty_and_none_are_safe(self):
        assert check_user_message("").triggered is False
        assert check_user_message(None).triggered is False

    def test_benign_message_is_safe(self):
        signal = check_user_message("Muraho, nashakaga kumenya ku bijyanye n'imihango.")
        assert signal.triggered is False
        assert signal.reason is None

    @pytest.mark.parametrize(
        "text",
        [
            "I want to kill myself",
            "I don't want to live anymore",
            "sometimes I think about suicide",
        ],
    )
    def test_suicidal_english(self, text):
        signal = check_user_message(text)
        assert signal.triggered is True
        assert signal.reason == "suicidal_ideation"

    @pytest.mark.parametrize("text", ["Ndumva nshaka kwiyahura", "sinshaka kubaho"])
    def test_suicidal_kinyarwanda(self, text):
        signal = check_user_message(text)
        assert signal.triggered is True
        assert signal.reason == "suicidal_ideation"

    def test_case_insensitive(self):
        assert check_user_message("I WANT TO DIE").triggered is True

    def test_leading_trailing_whitespace_is_stripped(self):
        assert check_user_message("   suicide   ").reason == "suicidal_ideation"

    @pytest.mark.parametrize(
        "text,reason",
        [
            ("he raped me", "gender_based_violence"),
            ("my boyfriend forced me", "gender_based_violence"),
            ("yankubise cyane", "gender_based_violence"),
            ("I have heavy bleeding", "medical_emergency"),
            ("I took pills to abort", "medical_emergency"),
            ("amaraso menshi", "medical_emergency"),
        ],
    )

    def test_other_categories(self, text, reason):
        signal = check_user_message(text)
        assert signal.triggered is True
        assert signal.reason == reason

    def test_matched_text_is_reported(self):
        signal = check_user_message("please, I want to die tonight")
        assert signal.matched_text == "want to die"

    
    @pytest.mark.parametrize("text", ["i'm 15", "i'm 17", "ndi w'imyaka 14"])
    def test_child_safeguarding_age(self, text):
        signal = check_user_message(text)
        assert signal.triggered is True
        assert signal.reason == "child_safeguarding_age"

    def test_adult_age_does_not_trigger_safeguarding(self):
        # 18/19 are outside the 10-17 safeguarding range.
        assert check_user_message("i'm 18").triggered is False

    def test_precedence_suicidal_beats_gbv(self):
        # Suicidal keywords are checked first, so they win when both appear.
        signal = check_user_message("he raped me and now I want to die")
        assert signal.reason == "suicidal_ideation"



class TestExtractEscalation:
    def test_no_tag_returns_text_unchanged(self):
        reason, cleaned = extract_escalation_from_response("Just a normal reply.")
        assert reason is None
        assert cleaned == "Just a normal reply."

    def test_tag_extracted_and_stripped(self):
        reason, cleaned = extract_escalation_from_response(
            "You are not alone. [ESCALATE: suicidal_ideation]"
        )
        assert reason == "suicidal_ideation"
        assert cleaned == "You are not alone."

    def test_tag_is_case_insensitive(self):
        reason, _ = extract_escalation_from_response("[escalate: GBV]")
        assert reason == "gbv"

    def test_multiple_tags_first_reason_kept_all_removed(self):
        reason, cleaned = extract_escalation_from_response(
            "a [ESCALATE: one] b [ESCALATE: two] c"
        )
        assert reason == "one"
        assert "ESCALATE" not in cleaned


class TestSafetyResponseText:
    @pytest.mark.parametrize(
        "reason", ["suicidal_ideation", "gender_based_violence", "medical_emergency"]
    )
    def test_known_reasons_return_text_both_languages(self, reason):
        assert safety_response_text(reason, "rw").strip() != ""
        assert safety_response_text(reason, "en").strip() != ""

    def test_suicidal_includes_hotline(self):
        assert "114" in safety_response_text("suicidal_ideation", "en")
        assert "114" in safety_response_text("suicidal_ideation", "rw")

    def test_gbv_includes_isange_number(self):
        assert "3029" in safety_response_text("gender_based_violence", "en")

    def test_unknown_reason_returns_empty(self):
        assert safety_response_text("something_else", "en") == ""

    def test_language_defaults_to_kinyarwanda(self):
        # Default lang is 'rw'; the RW copy differs from the EN copy.
        assert safety_response_text("medical_emergency") != safety_response_text(
            "medical_emergency", "en"
        )