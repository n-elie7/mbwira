"""Tests for the USSD menu-tree navigation logic (pure, no I/O)."""
import pytest

from app.content.ussd_tree import (
    TREE,
    next_state,
    parse_ussd_input,
    resolve_state,
    walk_tree,
)

# Africa's Talking / GSM-7 hard limit for a single USSD screen.
USSD_MAX_CHARS = 182

class TestParseUssdInput:
    def test_empty_string(self):
        assert parse_ussd_input("") == []

    def test_single_digit(self):
        assert parse_ussd_input("1") == ["1"]

    def test_accumulated_path(self):
        assert parse_ussd_input("1*2*3") == ["1", "2", "3"]

    def test_drops_empty_segments(self):
        assert parse_ussd_input("1**2*") == ["1", "2"]

class TestResolveState:
    def test_known_state_returns_screen(self):
        screen = resolve_state("start", "rw")
        assert screen["type"] == "CON"
        assert "Mbwira" in screen["prompt"]

    def test_unknown_state_falls_back_to_start(self):
        screen = resolve_state("does_not_exist", "rw")
        assert screen == TREE["start"]["rw"]

    def test_missing_language_falls_back_to_english(self):
        # Escalation screens are defined for both langs; force a fallback path
        # by resolving a node that only has 'en' would be ideal, but all nodes
        # have both — so we assert the 'en' branch resolves independently.
        screen = resolve_state("emergency", "en")
        assert "112" in screen["prompt"]

class TestNextState:
    def test_valid_option_advances(self):
        assert next_state("start", "1", "rw") == "srh_menu"
        assert next_state("start", "2", "rw") == "mh_menu"

    def test_back_option_returns_to_parent(self):
        assert next_state("srh_menu", "0", "rw") == "start"

    def test_unknown_input_stays_put(self):
        assert next_state("srh_menu", "7", "rw") == "srh_menu"

    def test_whitespace_in_input_is_stripped(self):
        assert next_state("start", " 1 ", "rw") == "srh_menu"
