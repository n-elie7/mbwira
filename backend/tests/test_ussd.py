"""Tests for the Africa's Talking USSD callback endpoint."""
from sqlalchemy import select

from app.models.db import Escalation, Session as DBSession


async def _post_ussd(client, session_id="ATSession1", text="", phone="+250788000000"):
    return await client.post(
        "/ussd",
        data={
            "sessionId": session_id,
            "serviceCode": "*123#",
            "phoneNumber": phone,
            "text": text,
        },
    )


async def test_root_menu_returns_con(client):
    resp = await _post_ussd(client, text="")
    assert resp.status_code == 200
    body = resp.text
    assert body.startswith("CON ")
    assert "Mbwira" in body


async def test_session_is_created_with_hashed_phone(client, db):
    await _post_ussd(client, session_id="ATHash", phone="+250788123456")
    sess = (
        await db.execute(select(DBSession).where(DBSession.session_id == "ATHash"))
    ).scalar_one()
    assert sess.channel == "ussd"
    # Raw phone number must never be stored — only a 64-char SHA-256 hash.
    assert sess.phone_hash is not None
    assert len(sess.phone_hash) == 64
    assert "250788123456" not in sess.phone_hash


async def test_same_session_id_is_reused(client, db):
    await _post_ussd(client, session_id="ATReuse", text="")
    await _post_ussd(client, session_id="ATReuse", text="1")

    rows = (
        await db.execute(select(DBSession).where(DBSession.session_id == "ATReuse"))
    ).scalars().all()
    assert len(rows) == 1


async def test_counselor_request_returns_end_and_escalates(client, db):
    resp = await _post_ussd(client, session_id="ATEsc", text="3")
    assert resp.text.startswith("END ")

    sess = (
        await db.execute(select(DBSession).where(DBSession.session_id == "ATEsc"))
    ).scalar_one()
    esc = (
        await db.execute(select(Escalation).where(Escalation.session_id == sess.id))
    ).scalar_one()
    assert esc.reason == "counselor_request"


async def test_suicidal_leaf_escalates(client, db):
    resp = await _post_ussd(client, session_id="ATSui", text="2*5")
    assert resp.text.startswith("END ")

    sess = (
        await db.execute(select(DBSession).where(DBSession.session_id == "ATSui"))
    ).scalar_one()
    esc = (
        await db.execute(select(Escalation).where(Escalation.session_id == sess.id))
    ).scalar_one()
    assert esc.reason == "suicidal_ideation"


async def test_missing_phone_number_is_allowed(client):
    # Africa's Talking may omit the number; endpoint must not crash.
    resp = await _post_ussd(client, session_id="ATNoPhone", phone="")
    assert resp.status_code == 200
