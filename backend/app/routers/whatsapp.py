"""WhatsApp Cloud API webhook — connects WhatsApp messages to our chat pipeline."""
import hashlib
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import httpx
from fastapi import HTTPException, Query

from app.config import settings

from app.models.db import Session, Message, get_db

from fastapi import APIRouter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])


def _hash_phone(phone: str) -> str:
    """One-way hash — we never store the raw number in the database."""
    return hashlib.sha256(phone.encode("utf-8")).hexdigest()

async def _get_or_create_session(db: AsyncSession, phone: str) -> Session:
    phone_hash = _hash_phone(phone)
    token = f"wa_{phone_hash[:32]}"

    result = await db.execute(select(Session).where(Session.session_token == token))
    session = result.scalar_one_or_none()
    if session:
        return session

    session = Session(session_token=token, channel="whatsapp", language="rw")
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session

async def _send_whatsapp_reply(phone: str, text: str) -> None:
    """Send a reply using the phone number from the incoming request — never stored."""
    if not settings.whatsapp_token or not settings.whatsapp_phone_number_id:
        logger.warning("WhatsApp not configured; would have sent: %s", text[:100])
        return

    url = f"{WHATSAPP_API_URL}/{settings.whatsapp_phone_number_id}/messages"
    headers = {"Authorization": f"Bearer {settings.whatsapp_token}"}
    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "text",
        "text": {"body": text[:4096]},
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(url, headers=headers, json=payload)
        if response.status_code >= 300:
            logger.error("WhatsApp send failed: %s %s", response.status_code, response.text)


@router.get("")
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
):
    """Meta's one-time verification handshake when connecting the webhook."""
    if hub_mode == "subscribe" and hub_verify_token == settings.whatsapp_verify_token:
        return int(hub_challenge) if hub_challenge and hub_challenge.isdigit() else hub_challenge
    raise HTTPException(403, "Verification failed")
