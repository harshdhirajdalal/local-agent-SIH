"""
Clean adapter boundary between the backend and the server-side AI/LLM.

Nothing in this file is tied to a specific LLM provider. The real
implementation (owned by the AI team) should be dropped in behind
`decide_next_action` without any changes to API routes, Pydantic models,
or session storage.

The prototype below is a deterministic mock so the rest of the system is
end-to-end testable before the real AI service exists.
"""

from models.agent_context import AgentContext
from models.action import Action, ActionType, ScrollDirection


def decide_next_action(context: AgentContext) -> Action:
    """
    Integration point for the server-side AI.

    Replace the body of this function with a call to the real agent/LLM
    service. It receives the full AgentContext (task, structured UI state,
    and a reference to the latest sanitized screenshot) and must return a
    single Action. Keep the signature the same.
    """
    return _mock_decide_next_action(context)


def _mock_decide_next_action(context: AgentContext) -> Action:
    """
    Temporary deterministic fallback used for the SIH prototype.

    Very small heuristic:
    1. If the task looks like a search task and a textbox exists that
       doesn't already contain the task text, TYPE into it.
    2. Else if a search/submit button exists, CLICK it.
    3. Else if there are elements below the fold (no strong signal available
       in this simple mock), SCROLL down a bit to look for more content.
    4. Otherwise, STOP -- nothing obvious left to do.
    """
    page_state = context.page_state
    elements = page_state.elements if page_state else []

    task_lower = context.task.lower()
    looks_like_search = any(keyword in task_lower for keyword in ["find", "search", "look for", "buy"])

    textbox = next(
        (el for el in elements if el.type.lower() in {"textbox", "input", "search"} and not el.sensitive),
        None,
    )
    button = next(
        (
            el
            for el in elements
            if el.type.lower() in {"button", "submit"}
            and any(k in (el.text or el.label or "").lower() for k in ["search", "submit", "go", "find"])
        ),
        None,
    )

    if looks_like_search and textbox is not None and (textbox.text or "") != context.task:
        return Action(action=ActionType.TYPE, target_id=textbox.id, value=context.task)

    if button is not None:
        return Action(action=ActionType.CLICK, target_id=button.id)

    if elements:
        return Action(action=ActionType.SCROLL, direction=ScrollDirection.DOWN, amount=500)

    return Action(action=ActionType.STOP, reason="No actionable elements found in current UI state.")
