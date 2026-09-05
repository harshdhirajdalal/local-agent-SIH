"""
Models describing detected UI elements on a page.

These are produced upstream by the local perception layer (DOM extraction /
computer vision) and sent to the backend as part of the structured, already
SANITIZED UI state. The backend never performs perception itself.
"""

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class BoundingBox(BaseModel):
    """Pixel-space bounding box for a UI element, used by downstream actions
    (e.g. click coordinates) when target_id alone isn't enough."""

    x: float
    y: float
    width: float
    height: float


class UIElement(BaseModel):
    """
    A single detected UI element.

    The schema is intentionally flexible so it can be populated from either
    DOM extraction or computer-vision based perception without changes here.
    """

    id: str = Field(..., description="Stable identifier for this element within the current page state")
    type: str = Field(..., description="Element type, e.g. 'textbox', 'button', 'link', 'checkbox'")
    text: Optional[str] = Field(None, description="Visible text content of the element, if any")
    label: Optional[str] = Field(None, description="Accessible / semantic label, if different from text")
    sensitive: bool = Field(False, description="Whether the local privacy layer flagged this element as sensitive")
    bbox: Optional[BoundingBox] = Field(None, description="Bounding box in page/screenshot coordinates")

    model_config = ConfigDict(extra="allow")  # keep this forward-compatible with richer perception payloads
