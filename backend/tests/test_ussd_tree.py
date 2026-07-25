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

