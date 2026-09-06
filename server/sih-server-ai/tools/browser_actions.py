"""Browser action tools for demo mode and live WebSocket sessions."""

from __future__ import annotations

from .browser_state import load_dom


def _fake_element(element_id):
    dom = load_dom()

    for element in dom.get("elements", []):
        if element.get("id") == element_id:
            return element

    return None


def _validate_fake_element(element_id, allow_sensitive=False):
    element = _fake_element(element_id)

    if element is None:
        return {
            "success": False,
            "error": f"Element '{element_id}' not found.",
        }

    if not element.get("visible", False):
        return {
            "success": False,
            "error": f"Element '{element_id}' is not visible.",
        }

    if not element.get("interactive", False):
        return {
            "success": False,
            "error": f"Element '{element_id}' is not interactive.",
        }

    if not allow_sensitive and element.get("sensitive", False):
        return {
            "success": False,
            "error": (
                f"Element '{element_id}' is sensitive. "
                "This action is disabled."
            ),
        }

    return None


def click(element_id, session=None):
    """Click a browser element by DOM ID."""

    if session is not None:
        return session.send_command_sync(
            "click",
            {"element_id": element_id},
        )

    error = _validate_fake_element(element_id)
    if error:
        return error

    return {
        "success": True,
        "action": "CLICK",
        "target_id": element_id,
    }


def type_text(element_id, text, session=None):
    """Type text into a visible, non-sensitive element."""

    if not isinstance(text, str):
        return {
            "success": False,
            "error": "Text must be a string.",
        }

    if session is not None:
        # The extension is also expected to enforce this rule.
        result = session.state
        if isinstance(result, dict):
            dom = result.get("dom") or {}
            for element in dom.get("elements", []):
                if element.get("id") == element_id and element.get("sensitive"):
                    return {
                        "success": False,
                        "error": (
                            f"Element '{element_id}' is sensitive. "
                            "Typing into sensitive fields is disabled."
                        ),
                    }

        return session.send_command_sync(
            "type_text",
            {
                "element_id": element_id,
                "text": text,
            },
        )

    error = _validate_fake_element(element_id)
    if error:
        return error

    return {
        "success": True,
        "action": "TYPE",
        "target_id": element_id,
        "value": text,
    }


def scroll(direction, amount, session=None):
    """Scroll the browser viewport."""

    valid_directions = {"up", "down", "left", "right"}

    if not isinstance(direction, str):
        return {
            "success": False,
            "error": "Scroll direction must be a string.",
        }

    direction = direction.lower().strip()

    if direction not in valid_directions:
        return {
            "success": False,
            "error": (
                f"Invalid scroll direction '{direction}'. "
                f"Expected one of: {sorted(valid_directions)}"
            ),
        }

    if not isinstance(amount, int) or isinstance(amount, bool) or amount <= 0:
        return {
            "success": False,
            "error": "Scroll amount must be a positive integer.",
        }

    if session is not None:
        return session.send_command_sync(
            "scroll",
            {"direction": direction, "amount": amount},
        )

    return {
        "success": True,
        "action": "SCROLL",
        "direction": direction,
        "amount": amount,
    }


def press_key(key, session=None):
    """Press a keyboard key in the browser."""

    if not isinstance(key, str) or not key.strip():
        return {
            "success": False,
            "error": "Key must be a non-empty string.",
        }

    key = key.strip()

    if session is not None:
        return session.send_command_sync(
            "press_key",
            {"key": key},
        )

    return {
        "success": True,
        "action": "PRESS_KEY",
        "key": key,
    }


def navigate(url, session=None):
    """Navigate the browser to a URL."""

    if not isinstance(url, str) or not url.strip():
        return {
            "success": False,
            "error": "URL must be a non-empty string.",
        }

    url = url.strip()

    if session is not None:
        return session.send_command_sync(
            "navigate",
            {"url": url},
        )

    return {
        "success": True,
        "action": "NAVIGATE",
        "url": url,
    }


def wait(milliseconds, session=None):
    """Wait for a specified number of milliseconds."""

    if (
        not isinstance(milliseconds, int)
        or isinstance(milliseconds, bool)
        or milliseconds < 0
    ):
        return {
            "success": False,
            "error": "Wait duration must be a non-negative integer.",
        }

    if session is not None:
        return session.send_command_sync(
            "wait",
            {"milliseconds": milliseconds},
        )

    return {
        "success": True,
        "action": "WAIT",
        "milliseconds": milliseconds,
    }


def register_tools(registry, session=None):
    """Register browser action tools, optionally bound to a live session."""

    registry.register(
        name="click",
        description=(
            "Click a visible, interactive browser element using its element ID."
        ),
        parameters={
            "type": "object",
            "properties": {
                "element_id": {
                    "type": "string",
                    "description": "ID of the element to click.",
                }
            },
            "required": ["element_id"],
        },
        handler=(lambda element_id: click(element_id, session)),
        category="browser_action",
        state_effect="may_change",
        risk="low",
    )

    registry.register(
        name="type_text",
        description=(
            "Type text into a visible, non-sensitive browser input "
            "element using its element ID."
        ),
        parameters={
            "type": "object",
            "properties": {
                "element_id": {
                    "type": "string",
                    "description": "ID of the input element.",
                },
                "text": {
                    "type": "string",
                    "description": "Text to type.",
                },
            },
            "required": ["element_id", "text"],
        },
        handler=(lambda element_id, text: type_text(element_id, text, session)),
        category="browser_action",
        state_effect="may_change",
        risk="low",
    )

    registry.register(
        name="scroll",
        description="Scroll the browser viewport.",
        parameters={
            "type": "object",
            "properties": {
                "direction": {
                    "type": "string",
                    "enum": ["up", "down", "left", "right"],
                    "description": "Direction to scroll.",
                },
                "amount": {
                    "type": "integer",
                    "description": "Number of pixels to scroll.",
                },
            },
            "required": ["direction", "amount"],
        },
        handler=(lambda direction, amount: scroll(direction, amount, session)),
        category="browser_action",
        state_effect="viewport",
        risk="safe",
    )

    registry.register(
        name="press_key",
        description="Press a keyboard key in the browser.",
        parameters={
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": "Key to press, such as ENTER, TAB, or ESC.",
                }
            },
            "required": ["key"],
        },
        handler=(lambda key: press_key(key, session)),
        category="browser_action",
        state_effect="may_change",
        risk="low",
    )

    registry.register(
        name="navigate",
        description="Navigate the browser to a specified URL.",
        parameters={
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Destination URL.",
                }
            },
            "required": ["url"],
        },
        handler=(lambda url: navigate(url, session)),
        category="navigation",
        state_effect="navigation",
        risk="medium",
    )

    registry.register(
        name="wait",
        description="Wait for a specified number of milliseconds.",
        parameters={
            "type": "object",
            "properties": {
                "milliseconds": {
                    "type": "integer",
                    "description": "How long to wait in milliseconds.",
                }
            },
            "required": ["milliseconds"],
        },
        handler=(lambda milliseconds: wait(milliseconds, session)),
        category="timing",
        state_effect="none",
        risk="safe",
    )
