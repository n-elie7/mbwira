"""Tests for the WhatsApp webhook verification handshake.

Only the GET verification handshake is covered here — it is pure and has no
external dependencies. (The POST message-receive path performs live Graph API
calls and is better exercised by integration tests.)
"""
import pytest

from app.config import settings

VERIFY_TOKEN = "verify-me"


@pytest.fixture(autouse=True)
def _set_verify_token(monkeypatch):
    monkeypatch.setattr(settings, "whatsapp_verify_token", VERIFY_TOKEN)


async def test_verify_success_echoes_numeric_challenge(client):
    resp = await client.get(
        "/whatsapp",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": VERIFY_TOKEN,
            "hub.challenge": "1234567",
        },
    )
    assert resp.status_code == 200
    assert resp.json() == 1234567


async def test_verify_wrong_token_is_forbidden(client):
    resp = await client.get(
        "/whatsapp",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "wrong",
            "hub.challenge": "1234567",
        },
    )
    assert resp.status_code == 403


async def test_verify_wrong_mode_is_forbidden(client):
    resp = await client.get(
        "/whatsapp",
        params={
            "hub.mode": "unsubscribe",
            "hub.verify_token": VERIFY_TOKEN,
            "hub.challenge": "1234567",
        },
    )
    assert resp.status_code == 403
