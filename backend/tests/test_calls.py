"""Tests for the anonymous video-call bridge."""
from sqlalchemy import select

from app.models.db import CallRequest, Session as DBSession
from app.routers.calls import _other_role


async def _make_web_session(db, session_id="web_call") -> DBSession:
    sess = DBSession(session_id=session_id, channel="web")
    db.add(sess)
    await db.commit()
    await db.refresh(sess)
    return sess


def test_other_role_is_symmetric():
    assert _other_role("user") == "counselor"
    assert _other_role("counselor") == "user"


async def test_request_call_creates_room(client, db):
    await _make_web_session(db, "web_req")
    resp = await client.post("/calls/request", json={"session_id": "web_req"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["room_id"].startswith("room_")
    assert body["status"] == "waiting"


async def test_request_call_unknown_session_404(client):
    resp = await client.post("/calls/request", json={"session_id": "web_missing"})
    assert resp.status_code == 404


async def test_request_call_is_idempotent_while_open(client, db):
    await _make_web_session(db, "web_dup")
    first = (await client.post("/calls/request", json={"session_id": "web_dup"})).json()
    second = (await client.post("/calls/request", json={"session_id": "web_dup"})).json()

    # Same open request reused rather than stacking duplicates on the dashboard.
    assert first["room_id"] == second["room_id"]
    rows = (
        await db.execute(select(CallRequest))
    ).scalars().all()
    assert len(rows) == 1


async def test_call_status_reports_waiting(client, db):
    await _make_web_session(db, "web_status")
    room = (await client.post("/calls/request", json={"session_id": "web_status"})).json()[
        "room_id"
    ]
    resp = await client.get(f"/calls/{room}/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "waiting"
    assert body["counselor_connected"] is False
    assert body["user_connected"] is False


async def test_status_unknown_room_404(client):
    resp = await client.get("/calls/room_nope/status")
    assert resp.status_code == 404


async def test_end_waiting_call_marks_cancelled(client, db):
    await _make_web_session(db, "web_end")
    room = (await client.post("/calls/request", json={"session_id": "web_end"})).json()[
        "room_id"
    ]
    resp = await client.post(f"/calls/{room}/end")
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"


async def test_end_unknown_room_404(client):
    resp = await client.post("/calls/room_nope/end")
    assert resp.status_code == 404
