"""
Structured UI state ("page state") for a session.

This is the sanitized, structured representation of what is currently on
screen -- URL, title, and detected elements. No raw screenshot data lives
here; that is handled separately by visual_context.py.
"""

from typing import List, Optional
from pydantic import BaseModel, Field

from models.ui import UIElement


class PageStateIn(BaseModel):
    """Payload the extension/perception layer POSTs to /sessions/{id}/state.

    session_id is taken from the URL path, not duplicated here, to avoid
    the two disagreeing.
    """

    url: str = Field(..., description="Current page URL")
    title: Optional[str] = Field(None, description="Current page title, if available")
    elements: List[UIElement] = Field(default_factory=list, description="Detected UI elements on the page")


class PageState(BaseModel):
    """Internal / response representation, includes session_id for clarity."""

    session_id: str
    url: str
    title: Optional[str] = None
    elements: List[UIElement] = Field(default_factory=list)
