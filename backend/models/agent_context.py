"""
AgentContext: the assembled bundle of information handed to the server-side
AI/agent service so it can decide the next Action.

This is the single, stable contract between the backend and the AI team.
The AI implementation can change freely as long as it keeps consuming this
shape and returning an Action.
"""

from typing import Optional
from pydantic import BaseModel

from models.page import PageState
from models.visual_context import SanitizedVisualContext


class AgentContext(BaseModel):
    session_id: str
    task: str
    page_state: Optional[PageState] = None
    visual_context: Optional[SanitizedVisualContext] = None
