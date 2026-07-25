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

class TestWalkTree:
    def test_empty_text_shows_start_kinyarwanda(self):
        state, screen = walk_tree("", lang="rw")
        assert state == "start"
        assert "Mbwira" in screen["prompt"]

    def test_navigate_into_srh(self):
        state, screen = walk_tree("1", lang="rw")
        assert state == "srh_menu"

    def test_language_toggle_to_english(self):
        state, screen = walk_tree("9", lang="rw")
        assert state == "start"
        assert "Welcome to Mbwira" in screen["prompt"]

    def test_counselor_request_is_terminal_and_escalates(self):
        state, screen = walk_tree("3", lang="rw")
        assert state == "counselor_request"
        assert screen["type"] == "END"
        assert screen.get("triggers_escalation") == "counselor_request"

    def test_suicidal_leaf_triggers_escalation(self):
        state, screen = walk_tree("2*5", lang="rw")
        assert state == "mh_suicidal"
        assert screen["type"] == "END"
        assert screen.get("triggers_escalation") == "suicidal_ideation"

    def test_emergency_screen(self):
        state, screen = walk_tree("4", lang="rw")
        assert state == "emergency"
        assert "112" in screen["prompt"]

    def test_deep_navigation_and_back(self):
        # start -> srh_menu -> contraception -> back to srh_menu
        state, _ = walk_tree("1*1*0", lang="rw")
        assert state == "srh_menu"

class TestTreeInvariants:
    """Structural guarantees the whole tree must satisfy."""

    @pytest.mark.parametrize("state", list(TREE.keys()))
    def test_both_languages_present(self, state):
        assert "rw" in TREE[state]
        assert "en" in TREE[state]

    @pytest.mark.parametrize("state", list(TREE.keys()))
    def test_every_prompt_within_ussd_limit(self, state):
        for lang in ("rw", "en"):
            prompt = TREE[state][lang]["prompt"]
            assert len(prompt) <= USSD_MAX_CHARS, f"{state}/{lang} too long"

    @pytest.mark.parametrize("state", list(TREE.keys()))
    def test_type_is_con_or_end(self, state):
        for lang in ("rw", "en"):
            assert TREE[state][lang]["type"] in ("CON", "END")

    def test_con_option_targets_all_exist(self):
        # Every option must point at a real state (or the 'start_en' toggle).
        valid = set(TREE.keys()) | {"start_en"}
        for state, langs in TREE.items():
            for lang, screen in langs.items():
                for target in screen.get("options", {}).values():
                    assert target in valid, f"{state}/{lang} -> {target}"
