"""WhatsApp Cloud API webhook — connects WhatsApp messages to our chat pipeline."""
import hashlib
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
