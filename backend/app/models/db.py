"""Database models. Keep data minimal — anonymity is the core design constraint."""
from datetime import datetime, timedelta
import uuid

from sqlalchemy import String, DateTime, Text, ForeignKey
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
    category: Mapped[str | None] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.utcnow() + timedelta(hours=24)
    )
class Message(Base):
    """A single chat message, tied only to a session token — never to a person."""
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"), index=True)
    sender: Mapped[str] = mapped_column(String(10))
    content: Mapped[str] = mapped_column(Text)
    risk_flag: Mapped[str | None] = mapped_column(String(20))
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
    # ------- engine / session factory -------
engine = create_async_engine(settings.database_url, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


