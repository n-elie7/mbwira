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


