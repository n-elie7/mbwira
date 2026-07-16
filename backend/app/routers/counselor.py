"""
Counselor dashboard API.

Simple password-protected endpoints for viewing and acting on escalations.
For MVP, we use a single shared password from config. For production,
replace with per-counselor accounts.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.db import Escalation, Session, Message, get_db

router = APIRouter(
    prefix="/counselor",
    tags=["counselor"],
)


def _check_auth(x_dashboard_password: str | None) -> None:
    if x_dashboard_password != settings.counselor_dashboard_password:
        raise HTTPException(401, "Bad dashboard password")


class EscalationOut(BaseModel):
    id: int
    session_id: str
    channel: str
    reason: str
    level: str
    status: str
    notes: str | None
    created_at: datetime
    message_count: int
    contact_available: bool
    age_minutes: int


class MessageOut(BaseModel):
    role: str
    content: str
    flagged: bool
    flag_reason: str | None
    created_at: datetime


class ResolveRequest(BaseModel):
    notes: str | None = None


@router.get("/escalations", response_model=list[EscalationOut])
async def list_escalations(
    status: str = "pending",
    x_dashboard_password: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
):
    _check_auth(x_dashboard_password)

    q = await db.execute(
        select(Escalation)
        .options(selectinload(Escalation.session).selectinload(Session.messages))
        .where(Escalation.status == status)
        .order_by(desc(Escalation.created_at))
        .limit(100)
    )

    out = []
    now = datetime.utcnow()

    for esc in q.scalars():
        age = int((now - esc.created_at).total_seconds() / 60)

        out.append(
            EscalationOut(
                id=esc.id,
                session_id=esc.session.session_id,
                channel=esc.session.channel,
                reason=esc.reason,
                level=esc.level,
                status=esc.status,
                notes=esc.notes,
                created_at=esc.created_at,
                message_count=len(esc.session.messages),
                contact_available=bool(esc.session.contact_number),
                age_minutes=age,
            )
        )

    return out

