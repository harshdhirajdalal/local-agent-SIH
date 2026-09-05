"""
In-memory session storage.

Everything that touches the raw `sessions` dict lives in this module.
No other module should reach into this dict directly -- that keeps it easy
to swap for Redis/Postgres/etc later without touching API or service code.

Structure of a session record:

{
    "session_id": str,
    "task": str,
    "page_state": PageState | None,
    "visual_context": SanitizedVisualContext | None,
    "latest_action": Action | None,
}
"""

from typing import Any, Dict, Optional

# session_id -> session record (plain dict of already-validated Pydantic objects)
_sessions: Dict[str, Dict[str, Any]] = {}


def session_exists(session_id: str) -> bool:
    return session_id in _sessions


def create_session(session_id: str, task: str) -> Dict[str, Any]:
    record = {
        "session_id": session_id,
        "task": task,
        "page_state": None,
        "visual_context": None,
        "latest_action": None,
    }
    _sessions[session_id] = record
    return record


def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    return _sessions.get(session_id)


def update_page_state(session_id: str, page_state) -> None:
    _sessions[session_id]["page_state"] = page_state


def update_visual_context(session_id: str, visual_context) -> None:
    _sessions[session_id]["visual_context"] = visual_context


def update_latest_action(session_id: str, action) -> None:
    _sessions[session_id]["latest_action"] = action


def get_task(session_id: str) -> Optional[str]:
    record = _sessions.get(session_id)
    return record["task"] if record else None


def get_page_state(session_id: str):
    record = _sessions.get(session_id)
    return record["page_state"] if record else None


def get_visual_context(session_id: str):
    record = _sessions.get(session_id)
    return record["visual_context"] if record else None


def get_latest_action(session_id: str):
    record = _sessions.get(session_id)
    return record["latest_action"] if record else None


def all_sessions() -> Dict[str, Dict[str, Any]]:
    """Mainly useful for debugging/tests."""
    return _sessions
