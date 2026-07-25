"""Tests for the counselor dashboard API (auth, stats, resolve, messages)."""
import pytest

from app.config import settings
from app.models.db import Escalation, Session as DBSession
from app.services.handoff import create_escalation

PASSWORD = "test-dashboard-pw"
AUTH = {"X-Dashboard-Password": PASSWORD}


@pytest.fixture(autouse=True)
def _set_password(monkeypatch):
    monkeypatch.setattr(settings, "counselor_dashboard_password", PASSWORD)


async def _seed_escalation(db, session_id="web_esc", reason="counselor_request"):
    sess = DBSession(session_id=session_id, channel="web")
    db.add(sess)
    await db.commit()
    await db.refresh(sess)
    esc = await create_escalation(db, sess, reason=reason)
    return sess, esc


async def test_escalations_requires_auth(client):
    resp = await client.get("/counselor/escalations")
    assert resp.status_code == 401


async def test_escalations_wrong_password(client):
    resp = await client.get(
        "/counselor/escalations", headers={"X-Dashboard-Password": "wrong"}
    )
    assert resp.status_code == 401


async def test_escalations_empty_list_with_auth(client):
    resp = await client.get("/counselor/escalations", headers=AUTH)
    assert resp.status_code == 200
    assert resp.json() == []


async def test_stats_requires_auth(client):
    resp = await client.get("/counselor/stats")
    assert resp.status_code == 401


async def test_stats_counts(client, db):
    await _seed_escalation(db, session_id="web_s1", reason="suicidal_ideation")

    resp = await client.get("/counselor/stats", headers=AUTH)
    assert resp.status_code == 200
    body = resp.json()
    assert body["sessions_total"] == 1
    assert body["escalations_total"] == 1
    assert body["escalations_pending"] == 1
    assert body["sessions_by_channel"] == {"web": 1}
    assert body["escalations_by_reason"] == {"suicidal_ideation": 1}


async def test_get_messages_unknown_escalation_404(client):
    resp = await client.get("/counselor/escalations/999/messages", headers=AUTH)
    assert resp.status_code == 404


async def test_resolve_escalation(client, db):
    _, esc = await _seed_escalation(db, session_id="web_resolve")

    resp = await client.post(
        f"/counselor/escalations/{esc.id}/resolve",
        json={"notes": "called the user"},
        headers=AUTH,
    )
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}

    refreshed = (
        await db.execute(Escalation.__table__.select().where(Escalation.id == esc.id))
    ).first()
    assert refreshed.status == "resolved"


async def test_resolve_unknown_escalation_404(client):
    resp = await client.post(
        "/counselor/escalations/999/resolve", json={}, headers=AUTH
    )
    assert resp.status_code == 404


async def test_list_calls_requires_auth(client):
    resp = await client.get("/counselor/calls")
    assert resp.status_code == 401


async def test_list_calls_empty(client):
    resp = await client.get("/counselor/calls", headers=AUTH)
    assert resp.status_code == 200
    assert resp.json() == []
