"""
Anonymous video call bridge between web chat users and counselors.

How it works:
  1. A user in the chat clicks the video call button, which calls
     POST /calls/request. This creates a CallRequest with a random,
     unguessable room id.
  2. That request shows up on the counselor dashboard. Whichever
     counselor is free joins the same room.
  3. Both sides open /call?room=<room_id> and exchange WebRTC connection
     details through the signaling WebSocket below. Once connected,
     audio/video flows directly between the two browsers — our server
     only passes along small connection messages and never sees the
     actual call.

No identity is ever exchanged — the room id is just a random token,
same idea as our session tokens.
"""
import logging

from fastapi import APIRouter
from pydantic import BaseModel
import secrets

from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db import CallRequest, Message, Session as DBSession, get_dbimport secrets

from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db import CallRequest, Message, Session as DBSession, get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/calls", tags=["calls"])

# Keeps track of who's connected to each call, in memory.
# room_id -> {"user": websocket, "counselor": websocket}
# Fine for now with a single server — would move to something like
# Redis if we ever need multiple servers running at once.
rooms: dict[str, dict] = {}


class RequestCallBody(BaseModel):
    session_id: str


class CallRequestOut(BaseModel):
    call_id: int
    room_id: str
    status: str

    @router.post("/request", response_model=CallRequestOut)
async def request_call(
    body: RequestCallBody, db: AsyncSession = Depends(get_db)
) -> CallRequestOut:
    """Starts a video call request for an anonymous session."""
    q = await db.execute(
        select(DBSession).where(DBSession.session_id == body.session_id)
    )
    sess = q.scalar_one_or_none()
    if not sess:
        raise HTTPException(404, "Session not found. Start a new session.")

    # If there's already an open request for this session, reuse it
    # instead of creating duplicates on the dashboard.
    q = await db.execute(
        select(CallRequest).where(
            CallRequest.session_id == sess.id,
            CallRequest.status.in_(("waiting", "active")),
        )
    )
    existing = q.scalar_one_or_none()
    if existing:
        return CallRequestOut(
            call_id=existing.id, room_id=existing.room_id, status=existing.status
        )

    call = CallRequest(
        session_id=sess.id,
        room_id="room_" + secrets.token_urlsafe(16),
    )
    db.add(call)
    db.add(Message(
        session_id=sess.id,
        role="system",
        content="[CALL] User requested a video call with a counselor.",
        flagged=False,
    ))
    await db.commit()
    await db.refresh(call)
    logger.info("Video call requested: session=%s room=%s", sess.session_id, call.room_id)
    return CallRequestOut(call_id=call.id, room_id=call.room_id, status=call.status)
@router.get("/{room_id}/status")
async def call_status(room_id: str, db: AsyncSession = Depends(get_db)):
    """Lets the waiting side check whether a counselor has joined yet."""
    q = await db.execute(select(CallRequest).where(CallRequest.room_id == room_id))
    call = q.scalar_one_or_none()
    if not call:
        raise HTTPException(404, "Call not found")
    peers = rooms.get(room_id, {})
    return {
        "status": call.status,
        "counselor_connected": "counselor" in peers,
        "user_connected": "user" in peers,
    }
