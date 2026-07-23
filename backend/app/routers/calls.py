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
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect

from app.models.db import AsyncSessionLocal

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
@router.post("/{room_id}/end")
async def end_call(room_id: str, db: AsyncSession = Depends(get_db)):
    """Marks a call as finished. Either side can call this, including
    automatically when someone closes the tab."""
    q = await db.execute(select(CallRequest).where(CallRequest.room_id == room_id))
    call = q.scalar_one_or_none()
    if not call:
        raise HTTPException(404, "Call not found")
    if call.status in ("waiting", "active"):
        call.status = "cancelled" if call.status == "waiting" else "ended"
        call.ended_at = datetime.utcnow()
        db.add(Message(
            session_id=call.session_id,
            role="system",
            content=f"[CALL] Video call {call.status}.",
            flagged=False,
        ))
        await db.commit()
    return {"ok": True, "status": call.status}
def _other_role(role: str) -> str:
    return "counselor" if role == "user" else "user"


@router.websocket("/ws/{room_id}")
async def signaling(ws: WebSocket, room_id: str, role: str = "user"):
    """Passes WebRTC connection messages back and forth between the
    two people in a call room."""
    await ws.accept()

    if role not in ("user", "counselor"):
        await ws.close(code=4400)
        return

    async with AsyncSessionLocal() as db:
        q = await db.execute(select(CallRequest).where(CallRequest.room_id == room_id))
        call = q.scalar_one_or_none()
        if not call or call.status in ("ended", "cancelled"):
            await ws.close(code=4404)
            return
        if role == "counselor" and call.status == "waiting":
            call.status = "active"
            call.started_at = datetime.utcnow()
            db.add(Message(
                session_id=call.session_id,
                role="system",
                content="[CALL] Counselor joined the video call.",
                flagged=False,
            ))
            await db.commit()

    peers = rooms.setdefault(room_id, {})
    if role in peers:
        # Someone's already connected with this role (e.g. a duplicate
        # browser tab) — refuse the new connection rather than replace it.
        await ws.close(code=4409)
        return
    peers[role] = ws

    # Let the new person know who's already here, and tell the other
    # side that someone just joined.
    await ws.send_json({"type": "room-state", "peers": [r for r in peers if r != role]})
    other = peers.get(_other_role(role))
    if other:
        await other.send_json({"type": "peer-joined", "role": role})

    try:
        while True:
            data = await ws.receive_json()
            target = peers.get(_other_role(role))
            if target:
                await target.send_json(data)
    except WebSocketDisconnect:
        pass
    finally:
        if peers.get(role) is ws:
            peers.pop(role, None)
        other = peers.get(_other_role(role))
        if other:
            try:
                await other.send_json({"type": "peer-left", "role": role})
            except Exception:
                pass
        if not peers:
            rooms.pop(room_id, None)
