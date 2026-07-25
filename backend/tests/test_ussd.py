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
