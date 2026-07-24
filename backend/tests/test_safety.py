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
    