"""
Handles updates to a session's structured UI state.
"""

from typing import Optional

from storage import memory_store
from models.page import PageState, PageStateIn
from services.session_service import require_session


def update_state(session_id: str, payload: PageStateIn) -> PageState:
    require_session(session_id)

    page_state = PageState(
        session_id=session_id,
        url=payload.url,
        title=payload.title,
        elements=payload.elements,
    )
    memory_store.update_page_state(session_id, page_state)
    return page_state


def get_state(session_id: str) -> Optional[PageState]:
    require_session(session_id)
    return memory_store.get_page_state(session_id)
