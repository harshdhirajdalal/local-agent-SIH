"""Browser-state tools with support for live and demo sessions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional


STATE_DIR = (
    Path(__file__).resolve().parent.parent
    / "test_data"
    / "browser_state"
)


def load_dom(session=None) -> dict[str, Any]:
    """Return live session DOM when available, otherwise demo DOM."""

    if session is not None and session.state is not None:
        dom = session.state.get("dom")
        if isinstance(dom, dict):
            return dom

    dom_path = STATE_DIR / "dom.json"

    with open(dom_path, "r", encoding="utf-8") as file:
        return json.load(file)


def load_visual(session=None) -> dict[str, Any]:
    """Return live session visual state when available, otherwise demo visual state."""

    if session is not None and session.state is not None:
        visual = session.state.get("visual")
        if isinstance(visual, dict):
            return visual

    visual_path = STATE_DIR / "visual.json"

    with open(visual_path, "r", encoding="utf-8") as file:
        return json.load(file)


def get_page_info(session=None):
    """Return basic information about the current browser page."""

    if session is not None and session.state is not None:
        state = session.state
        return {
            "url": (state.get("page") or {}).get("url"),
            "title": (state.get("page") or {}).get("title"),
            "viewport": state.get("viewport"),
            "scroll": state.get("scroll"),
        }

    dom = load_dom()

    return {
        "url": dom.get("url"),
        "title": dom.get("title"),
        "viewport": dom.get("viewport"),
        "scroll": dom.get("scroll"),
    }


def get_interactive_elements(session=None):
    """Return visible interactive DOM elements without sensitive values."""

    dom = load_dom(session)
    elements = []

    for element in dom.get("elements", []):
        if not element.get("visible"):
            continue
        if not element.get("interactive"):
            continue

        elements.append({
            "id": element.get("id"),
            "type": element.get("type"),
            "label": element.get("label"),
            "placeholder": element.get("placeholder"),
            "text": element.get("text"),
            "bbox": element.get("bbox"),
            "sensitive": element.get("sensitive", False),
        })

    return elements


def _element_matches_query(element: dict[str, Any], query: str) -> bool:
    """Apply direct and small semantic-query matching."""

    searchable_fields = [
        "id",
        "type",
        "label",
        "placeholder",
        "text",
    ]

    searchable = " ".join(
        str(element.get(field, ""))
        for field in searchable_fields
    ).lower()

    if query in searchable:
        return True

    semantic_queries = {
        "search box": {
            "required_type": "textbox",
            "required_text": "search",
        },
        "search field": {
            "required_type": "textbox",
            "required_text": "search",
        },
        "input field": {
            "required_type": "textbox",
            "required_text": None,
        },
        "text field": {
            "required_type": "textbox",
            "required_text": None,
        },
        "input": {
            "required_type": "textbox",
            "required_text": None,
        },
        "box": {
            "required_type": "textbox",
            "required_text": None,
        },
        "field": {
            "required_type": "textbox",
            "required_text": None,
        },
        "dropdown": {
            "required_type": None,
            "required_text": "dropdown",
        },
        "menu": {
            "required_type": None,
            "required_text": "menu",
        },
    }

    rule = semantic_queries.get(query)
    if rule is None:
        return False

    element_type = str(element.get("type", "")).lower()
    searchable_text = (
        str(element.get("id", "")) + " "
        + str(element.get("label", "")) + " "
        + str(element.get("placeholder", ""))
    ).lower()

    type_matches = (
        rule["required_type"] is None
        or element_type == rule["required_type"]
    )

    text_matches = (
        rule["required_text"] is None
        or rule["required_text"] in searchable_text
    )

    return type_matches and text_matches


def find_elements(query, session=None):
    """Search the current DOM for elements matching a natural-language query."""

    if not isinstance(query, str):
        return []

    query = query.lower().strip()
    if not query:
        return []

    dom = load_dom(session)
    results = []

    for element in dom.get("elements", []):
        if not _element_matches_query(element, query):
            continue

        results.append({
            "id": element.get("id"),
            "type": element.get("type"),
            "label": element.get("label"),
            "text": element.get("text"),
            "placeholder": element.get("placeholder"),
            "bbox": element.get("bbox"),
            "visible": element.get("visible"),
            "interactive": element.get("interactive"),
            "sensitive": element.get("sensitive", False),
        })

    return results


def get_element(element_id, session=None):
    """Retrieve one DOM element by ID without returning its value."""

    dom = load_dom(session)

    for element in dom.get("elements", []):
        if element.get("id") != element_id:
            continue

        return {
            "id": element.get("id"),
            "type": element.get("type"),
            "label": element.get("label"),
            "text": element.get("text"),
            "placeholder": element.get("placeholder"),
            "bbox": element.get("bbox"),
            "visible": element.get("visible"),
            "interactive": element.get("interactive"),
            "sensitive": element.get("sensitive", False),
        }

    return {
        "error": f"Element '{element_id}' not found."
    }


def get_visual_context(session=None):
    """Return sanitized visual-perception results."""

    visual = load_visual(session)

    return {
        "source": visual.get("source"),
        "image": visual.get("image"),
        "elements": visual.get("elements", []),
        "screenshot": visual.get("screenshot"),
        "privacy": visual.get("privacy", {}),
    }


def register_tools(registry, session=None):
    """Register browser-state tools, optionally bound to one live session."""

    registry.register(
        name="get_page_info",
        description=(
            "Get basic information about the current browser page, "
            "including its URL, title, viewport, and scroll position."
        ),
        parameters={
            "type": "object",
            "properties": {},
            "required": [],
        },
        handler=(lambda: get_page_info(session)),
        category="inspection",
        state_effect="none",
        risk="safe",
    )

    registry.register(
        name="find_elements",
        description=(
            "Search the current browser DOM for UI elements matching "
            "a natural-language query. Use this to find things such "
            "as search boxes, buttons, links, or form fields."
        ),
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The UI element or text to search for.",
                }
            },
            "required": ["query"],
        },
        handler=(lambda query: find_elements(query, session)),
        category="inspection",
        state_effect="none",
        risk="safe",
    )

    registry.register(
        name="get_element",
        description=(
            "Get detailed information about a browser UI element "
            "using its element ID. Never returns the field value."
        ),
        parameters={
            "type": "object",
            "properties": {
                "element_id": {
                    "type": "string",
                    "description": "The ID of the browser element.",
                }
            },
            "required": ["element_id"],
        },
        handler=(lambda element_id: get_element(element_id, session)),
        category="inspection",
        state_effect="none",
        risk="safe",
    )

    registry.register(
        name="get_visual_context",
        description=(
            "Get the current visual perception results from the browser "
            "screenshot. Use this when DOM information is insufficient "
            "or when visual confirmation is needed."
        ),
        parameters={
            "type": "object",
            "properties": {},
            "required": [],
        },
        handler=(lambda: get_visual_context(session)),
        category="perception",
        state_effect="none",
        risk="safe",
    )

    registry.register(
        name="get_interactive_elements",
        description=(
            "Get the currently visible interactive elements on the page."
        ),
        parameters={
            "type": "object",
            "properties": {},
            "required": [],
        },
        handler=(lambda: get_interactive_elements(session)),
        category="inspection",
        state_effect="none",
        risk="safe",
    )
