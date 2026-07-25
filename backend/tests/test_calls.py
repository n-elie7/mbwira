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
