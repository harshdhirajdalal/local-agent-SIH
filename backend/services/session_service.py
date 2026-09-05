"""
Session lifecycle logic. Wraps storage/memory_store.py so API routers never
touch the raw store directly.
"""

from fastapi import HTTPException

from storage import memory_store
from models.session import SessionCreateRequest, SessionCreateResponse


def create_session(payload: SessionCreateRequest) -> SessionCreateResponse:
    """
    Register a new session using the extension-provided session_id.

    If the session_id already exists we do NOT silently overwrite it --
    that could wipe an in-progress task's state. We surface a 409-style
    error via HTTPException so the caller (extension) can decide what to do
    (e.g. start a fresh session_id, or explicitly reset).
    """
    if memory_store.session_exists(payload.session_id):
        raise HTTPException(
            status_code=409,
            detail=(
                f"Session '{payload.session_id}' already exists. "
                "Use a new session_id for a new task, or call the reset "
                "flow explicitly if you intend to reuse this id."
            ),
        )

    memory_store.create_session(payload.session_id, payload.task)

    return SessionCreateResponse(
        session_id=payload.session_id,
        task=payload.task,
        status="created",
        message="Session registered successfully.",
    )


def require_session(session_id: str) -> dict:
    """Fetch a session record or raise 404. Central place for this check."""
    record = memory_store.get_session(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' does not exist.")
    return record
