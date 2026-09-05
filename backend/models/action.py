"""
Structured Action returned by the agent service and forwarded to the
Browser Extension after backend-side validation.
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class ActionType(str, Enum):
    CLICK = "CLICK"
    TYPE = "TYPE"
    SCROLL = "SCROLL"
    WAIT = "WAIT"
    STOP = "STOP"


class ScrollDirection(str, Enum):
    UP = "UP"
    DOWN = "DOWN"
    LEFT = "LEFT"
    RIGHT = "RIGHT"


class Action(BaseModel):
    """
    A single structured action for the Browser Extension to execute.

    Fields are optional/overloaded across action types on purpose so this
    stays a single simple shape that's easy for the extension to parse:

    CLICK -> target_id
    TYPE  -> target_id, value
    SCROLL-> direction, amount
    WAIT  -> duration_ms
    STOP  -> reason
    """

    action: ActionType
    target_id: Optional[str] = Field(None, description="UI element id this action applies to (CLICK, TYPE)")
    value: Optional[str] = Field(None, description="Text to type (TYPE)")
    direction: Optional[ScrollDirection] = Field(None, description="Scroll direction (SCROLL)")
    amount: Optional[int] = Field(None, description="Scroll amount in pixels (SCROLL)")
    duration_ms: Optional[int] = Field(None, description="Wait duration in milliseconds (WAIT)")
    reason: Optional[str] = Field(None, description="Why the agent decided to stop (STOP)")
