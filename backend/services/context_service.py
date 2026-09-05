"""
Assembles the AgentContext handed to the server-side AI/agent service.
"""

from storage import memory_store
from models.agent_context import AgentContext
from services.session_service import require_session


def build_agent_context(session_id: str) -> AgentContext:
    record = require_session(session_id)

    return AgentContext(
        session_id=session_id,
        task=record["task"],
        page_state=record.get("page_state"),
        visual_context=record.get("visual_context"),
    )
