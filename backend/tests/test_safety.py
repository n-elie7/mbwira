"""Tests for the crisis-detection safety layer, with different scenarios like languages and edge cases."""


import pytest

from app.services.safety import (
    check_user_message,
    extract_escalation_from_response,
    safety_response_text,
)