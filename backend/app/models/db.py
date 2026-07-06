"""Database models. Keep data minimal — anonymity is the core design constraint."""
from datetime import datetime, timedelta
import uuid

from sqlalchemy import String, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.config import settings


class Base(DeclarativeBase):
    pass


class Session(Base):
    """A user conversation session. No PII — only a random session token."""
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_token: Mapped[str] = mapped_column(
        String(36), unique=True, index=True, default=lambda: str(uuid.uuid4())
    )
    channel: Mapped[str] = mapped_column(String(16), default="web")  # 'ussd' | 'whatsapp' | 'web'
    language: Mapped[str] = mapped_column(String(8), default="rw")  # 'rw' | 'en'
    category: Mapped[str | None] = mapped_column(String(30))
    escalated: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.utcnow() + timedelta(hours=24)
    )

    messages: Mapped[list["Message"]] = relationship(back_populates="session")
    escalation: Mapped["Escalation | None"] = relationship(back_populates="session")


class Message(Base):
    """A single chat message, tied only to a session token — never to a person."""
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"), index=True)
    sender: Mapped[str] = mapped_column(String(10))
    content: Mapped[str] = mapped_column(Text)
    flagged: Mapped[bool] = mapped_column(Boolean, default=False)
    flag_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    session: Mapped["Session"] = relationship(back_populates="messages")


class Referral(Base):
    """Real-world help resources (e.g. Isange One Stop Centres, hotlines)."""
    __tablename__ = "referrals"

    id: Mapped[int] = mapped_column(primary_key=True)
    category: Mapped[str] = mapped_column(String(30))
    region: Mapped[str | None] = mapped_column(String(50))
    name: Mapped[str] = mapped_column(String(120))
    contact_info: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)


class Escalation(Base):
    """When a user needs a human — counselor, CHW, or emergency services."""
    __tablename__ = "escalations"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), unique=True)
    level: Mapped[str] = mapped_column(String(16))  # 'counselor' | 'chw' | 'emergency'
    reason: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending | taken | resolved
    counselor_id: Mapped[int | None] = mapped_column(ForeignKey("counselors.id"), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
