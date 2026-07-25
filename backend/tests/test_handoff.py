"""Tests for the escalation hand-off service."""
from app.models.db import Escalation, Session as DBSession
from app.services.handoff import create_escalation


async def _make_session(db, session_id="web_test") -> DBSession:
    sess = DBSession(session_id=session_id, channel="web")
    db.add(sess)
    await db.commit()
    await db.refresh(sess)
    return sess


async def test_creates_escalation_and_flags_session(db):
    sess = await _make_session(db)

    esc = await create_escalation(db, sess, reason="suicidal_ideation", level="counselor")

    assert esc.id is not None
    assert esc.reason == "suicidal_ideation"
    assert esc.level == "counselor"
    assert esc.status == "pending"
    assert sess.escalated is True


async def test_notes_are_persisted(db):
    sess = await _make_session(db)
    esc = await create_escalation(db, sess, reason="gbv", notes="from chat")
    assert esc.notes == "from chat"


async def test_default_level_is_counselor(db):
    sess = await _make_session(db)
    esc = await create_escalation(db, sess, reason="counselor_request")
    assert esc.level == "counselor"


async def test_duplicate_pending_escalation_is_not_created(db):
    sess = await _make_session(db)

    first = await create_escalation(db, sess, reason="suicidal_ideation")
    second = await create_escalation(db, sess, reason="something_else")

    # Same row returned; the second call must not stack a duplicate.
    assert second.id == first.id
    assert second.reason == "suicidal_ideation"  # original reason preserved

    rows = (await db.execute(Escalation.__table__.select())).all()
    assert len(rows) == 1
