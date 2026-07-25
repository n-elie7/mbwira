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

@router.get(
    "/escalations/{escalation_id}/messages",
    response_model=list[MessageOut],
)
async def get_messages(
    escalation_id: int,
    x_dashboard_password: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
):
    _check_auth(x_dashboard_password)

    q = await db.execute(
        select(Escalation).where(Escalation.id == escalation_id)
    )

    esc = q.scalar_one_or_none()

    if not esc:
        raise HTTPException(404, "Not found")

    messages = await db.execute(
        select(Message)
        .where(Message.session_id == esc.session_id)
        .order_by(Message.created_at.asc())
    )

    return [
        MessageOut(
            role=msg.role,
            content=msg.content,
            flagged=msg.flagged,
            flag_reason=msg.flag_reason,
            created_at=msg.created_at,
        )
        for msg in messages.scalars()
    ]


@router.post("/escalations/{escalation_id}/resolve")
async def resolve_escalation(
    escalation_id: int,
    body: ResolveRequest,
    x_dashboard_password: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
):
    _check_auth(x_dashboard_password)

    q = await db.execute(
        select(Escalation).where(Escalation.id == escalation_id)
    )

    esc = q.scalar_one_or_none()

    if not esc:
        raise HTTPException(404, "Not found")

    esc.status = "resolved"
    esc.resolved_at = datetime.utcnow()

    if body.notes:
        esc.notes = (esc.notes or "") + f"\n[resolved] {body.notes}"

    await db.commit()

    return {"ok": True}

@router.get("/stats")
async def stats(
    x_dashboard_password: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
):
    _check_auth(x_dashboard_password)

    total_sessions = (
        await db.execute(select(Session))
    ).scalars().all()

    total_escalations = (
        await db.execute(select(Escalation))
    ).scalars().all()

    pending = [
        e for e in total_escalations
        if e.status == "pending"
    ]

    by_channel = {}

    for session in total_sessions:
        by_channel[session.channel] = (
            by_channel.get(session.channel, 0) + 1
        )

    by_reason = {}

    for escalation in total_escalations:
        by_reason[escalation.reason] = (
            by_reason.get(escalation.reason, 0) + 1
        )

    return {
        "sessions_total": len(total_sessions),
        "sessions_by_channel": by_channel,
        "escalations_total": len(total_escalations),
        "escalations_pending": len(pending),
        "escalations_by_reason": by_reason,
    }

# -------- Callback actions --------

class RevealContactRequest(BaseModel):
    reason: str


@router.post(
    "/escalations/{escalation_id}/reveal-contact"
)
async def reveal_contact(
    escalation_id: int,
    body: RevealContactRequest,
    x_dashboard_password: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Reveal the user's phone number to the counselor.
    The action is recorded for auditing.
    """

    _check_auth(x_dashboard_password)

    q = await db.execute(
        select(Escalation)
        .options(selectinload(Escalation.session))
        .where(Escalation.id == escalation_id)
    )

    esc = q.scalar_one_or_none()

    if not esc:
        raise HTTPException(404, "Not found")

    if not esc.session.contact_number:
        raise HTTPException(
            404,
            "No contact number on file for this session.",
        )

    db.add(
        Message(
            session_id=esc.session.id,
            role="system",
            content=(
                "[AUDIT] Contact number revealed to counselor. "
                f"Reason: {body.reason}"
            ),
            flagged=False,
        )
    )

    if esc.status == "pending":
        esc.status = "taken"

    await db.commit()

    return {
        "contact_number": esc.session.contact_number,
        "channel": esc.session.channel,
    }


class SendOutboundMessage(BaseModel):
    text: str


@router.post(
    "/escalations/{escalation_id}/send-message"
)
async def send_outbound_message(
    escalation_id: int,
    body: SendOutboundMessage,
    x_dashboard_password: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Send WhatsApp message from counselor dashboard.
    """

    _check_auth(x_dashboard_password)

    q = await db.execute(
        select(Escalation)
        .options(selectinload(Escalation.session))
        .where(Escalation.id == escalation_id)
    )

    esc = q.scalar_one_or_none()

    if not esc:
        raise HTTPException(404, "Not found")

    sess = esc.session

    if sess.channel != "whatsapp" or not sess.contact_number:
        raise HTTPException(
            400,
            "Outbound messaging only supported for WhatsApp "
            "sessions with a known number.",
        )

    from app.routers.whatsapp import _send_whatsapp

    await _send_whatsapp(
        sess.contact_number,
        body.text,
    )

    db.add(
        Message(
            session_id=sess.id,
            role="assistant",
            content=f"[COUNSELOR] {body.text}",
            flagged=False,
        )
    )

    if esc.status == "pending":
        esc.status = "taken"

    await db.commit()

    return {"ok": True}

