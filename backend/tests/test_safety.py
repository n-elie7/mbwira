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