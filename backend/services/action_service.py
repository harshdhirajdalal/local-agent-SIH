"""
Validates actions produced by the agent service before they are returned to
the Browser Extension. This is the boundary between AI output and browser
automation -- malformed or unsafe actions must never pass through silently.
"""

from typing import Optional

from fastapi import HTTPException

from models.action import Action, ActionType
from models.page import PageState


def validate_action(action: Action, page_state: Optional[PageState]) -> Action:
    element_ids = {el.id for el in page_state.elements} if page_state else set()

    if action.action == ActionType.CLICK:
        if not action.target_id:
            raise HTTPException(status_code=400, detail="CLICK action is missing target_id.")
        if element_ids and action.target_id not in element_ids:
            raise HTTPException(
                status_code=400,
                detail=f"CLICK target_id '{action.target_id}' not found in current UI state.",
            )

    elif action.action == ActionType.TYPE:
        if not action.target_id:
            raise HTTPException(status_code=400, detail="TYPE action is missing target_id.")
        if element_ids and action.target_id not in element_ids:
            raise HTTPException(
                status_code=400,
                detail=f"TYPE target_id '{action.target_id}' not found in current UI state.",
            )
        if not action.value:
            raise HTTPException(status_code=400, detail="TYPE action is missing a non-empty value.")

    elif action.action == ActionType.SCROLL:
        if action.direction is None:
            raise HTTPException(status_code=400, detail="SCROLL action is missing direction.")

    elif action.action == ActionType.WAIT:
        if action.duration_ms is None or action.duration_ms < 0:
            raise HTTPException(status_code=400, detail="WAIT action requires a non-negative duration_ms.")

    elif action.action == ActionType.STOP:
        pass  # no additional required fields

    else:
        raise HTTPException(status_code=400, detail=f"Unsupported action type: {action.action}")

    return action
