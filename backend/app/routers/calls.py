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
