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


async def test_escalations_with_pending_row_does_not_crash(client, db):
    # Regression: list_escalations used to read Session.contact_number, which
    # does not exist on the anonymised model, and 500'd whenever any pending
    # escalation existed — which broke the whole dashboard load.
    await _seed_escalation(db, session_id="web_pending", reason="suicidal_ideation")

    resp = await client.get("/counselor/escalations?status=pending", headers=AUTH)
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) == 1
    assert rows[0]["reason"] == "suicidal_ideation"
    # No dialable number is ever stored for anonymised sessions.
    assert rows[0]["contact_available"] is False


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


async def test_join_call_returns_room_id(client, db):
    # Regression: join_call was gutted to `...` and returned null, so the
    # dashboard's `data.room_id` threw and the counselor could never open the
    # call page. It must hand back the room id and status.
    from app.models.db import CallRequest, Session as DBSession

    sess = DBSession(session_id="web_call_join", channel="web")
    db.add(sess)
    await db.commit()
    await db.refresh(sess)
    call = CallRequest(session_id=sess.id, room_id="room_test_join")
    db.add(call)
    await db.commit()
    await db.refresh(call)

    resp = await client.post(f"/counselor/calls/{call.id}/join", headers=AUTH)
    assert resp.status_code == 200
    body = resp.json()
    assert body["room_id"] == "room_test_join"
    assert body["status"] == "waiting"


async def test_join_call_requires_auth(client):
    resp = await client.post("/counselor/calls/1/join")
    assert resp.status_code == 401


async def test_join_unknown_call_404(client):
    resp = await client.post("/counselor/calls/999/join", headers=AUTH)
    assert resp.status_code == 404
