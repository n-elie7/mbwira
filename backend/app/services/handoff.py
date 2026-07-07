"""Utilities for creating and tracking support escalations 
This service ensures only one pending escalation exists for a session"""
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db import Escalation, Session

logger = logging.getLogger(__name__)


async def create_escalation(
    db: AsyncSession,
    session: Session,
    reason: str,
    level: str = "counselor",
    notes: str | None = None,
) -> Escalation:
    """Create a new escalation when needed
    If a pending escalation already exists, return it instead of creating a duplicate record."""
    # if already escalated with same reason, don't duplicate.
    existing = await db.execute(
        select(Escalation).where(Escalation.session_id == session.id)
    )
    existing = existing.scalar_one_or_none()
    if existing and existing.status == "pending":
        logger.info(
            "Escalation already pending for session %s",
            session.session_token,
        )
        return existing

    escalation = Escalation(
        session_id=session.id,
        level=level,
        reason=reason,
        status="pending",
        notes=notes,
    )
    db.add(escalation)
    session.escalated = True
    await db.commit()
    await db.refresh(escalation)
    await db.refresh(session)
    logger.warning(
        "Escalation created: session=%s reason=%s level=%s",
        session.session_token, reason, level,
    )
    return escalation