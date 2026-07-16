"""WhatsApp Cloud API webhook — connects WhatsApp messages to our chat pipeline."""
import hashlib
import logging

from fastapi import APIRouter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])


def _hash_phone(phone: str) -> str:
    """One-way hash — we never store the raw number in the database."""
    return hashlib.sha256(phone.encode("utf-8")).hexdigest()
