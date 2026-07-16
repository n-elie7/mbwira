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


