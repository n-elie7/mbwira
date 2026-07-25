"""Tests for the web chat endpoint.

The LLM is stubbed (``stub_llm``) so these tests are deterministic and make no
network calls. They focus on the pipeline the router owns: session handling,
safety pre-screening, escalation, and the safety fallback text.
"""
import pytest

from app.models.db import Escalation, Message, Session as DBSession
from sqlalchemy import select


async def _new_session_id(client) -> str:
    resp = await client.get("/chat/new")
    assert resp.status_code == 200
    return resp.json()["session_id"]


async def test_new_session_creates_web_session(client, db):
    sid = await _new_session_id(client)
    assert sid.startswith("web_")

    sess = (
        await db.execute(select(DBSession).where(DBSession.session_id == sid))
    ).scalar_one()
    assert sess.channel == "web"


async def test_chat_unknown_session_returns_404(client, stub_llm):
    resp = await client.post(
        "/chat", json={"session_id": "web_nope", "message": "hi"}
    )
    assert resp.status_code == 404


async def test_benign_chat_returns_reply_without_escalation(client, stub_llm):
    stub_llm.reply = "Murakoze kubaza."
    sid = await _new_session_id(client)

    resp = await client.post(
        "/chat", json={"session_id": sid, "message": "Nashaka kumenya ku mihango"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["reply"] == "Murakoze kubaza."
    assert body["escalated"] is False
    assert body["escalation_reason"] is None


async def test_suicidal_message_escalates_and_appends_safety_text(client, stub_llm, db):
    stub_llm.reply = "I'm really glad you reached out."
    sid = await _new_session_id(client)

    resp = await client.post(
        "/chat",
        json={"session_id": sid, "message": "I want to die", "language": "en"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["escalated"] is True
    assert body["escalation_reason"] == "suicidal_ideation"
    # Bilingual safety tail with the crisis hotline is appended to the reply.
    assert "114" in body["reply"]

    # An escalation row was persisted for this session.
    sess = (
        await db.execute(select(DBSession).where(DBSession.session_id == sid))
    ).scalar_one()
    esc = (
        await db.execute(select(Escalation).where(Escalation.session_id == sess.id))
    ).scalar_one()
    assert esc.reason == "suicidal_ideation"
    assert esc.level == "counselor"


async def test_medical_emergency_escalates_at_emergency_level(client, stub_llm, db):
    sid = await _new_session_id(client)
    resp = await client.post(
        "/chat",
        json={"session_id": sid, "message": "I have heavy bleeding", "language": "en"},
    )
    body = resp.json()
    assert body["escalation_reason"] == "medical_emergency"

    sess = (
        await db.execute(select(DBSession).where(DBSession.session_id == sid))
    ).scalar_one()
    esc = (
        await db.execute(select(Escalation).where(Escalation.session_id == sess.id))
    ).scalar_one()
    assert esc.level == "emergency"


async def test_escalation_from_llm_tag(client, stub_llm, db):
    # No crisis keyword in the user text; the model itself asks to escalate.
    stub_llm.reply = "Let me connect you. [ESCALATE: counselor_request]"
    sid = await _new_session_id(client)

    resp = await client.post(
        "/chat", json={"session_id": sid, "message": "I need to talk to someone"}
    )
    body = resp.json()
    assert body["escalated"] is True
    assert body["escalation_reason"] == "counselor_request"
    # The tag itself is stripped from the user-visible reply.
    assert "ESCALATE" not in body["reply"]


async def test_messages_are_persisted(client, stub_llm, db):
    stub_llm.reply = "reply text"
    sid = await _new_session_id(client)
    await client.post("/chat", json={"session_id": sid, "message": "hello there"})

    sess = (
        await db.execute(select(DBSession).where(DBSession.session_id == sid))
    ).scalar_one()
    msgs = (
        await db.execute(select(Message).where(Message.session_id == sess.id))
    ).scalars().all()
    roles = [m.role for m in msgs]
    assert "user" in roles and "assistant" in roles
