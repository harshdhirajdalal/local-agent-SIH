from urllib.parse import urlparse


SAFE_SCHEMES = {
    "http",
    "https",
}


BLOCKED_SCHEMES = {
    "javascript",
    "data",
    "file",
    "vbscript",
}


def validate_url(url: str):
    """Allow only normal web URLs."""

    if not isinstance(url, str) or not url.strip():
        return {
            "success": False,
            "error": "URL must be a non-empty string.",
        }

    parsed = urlparse(url.strip())

    if parsed.scheme.lower() in BLOCKED_SCHEMES:
        return {
            "success": False,
            "error": f"URL scheme '{parsed.scheme}' is blocked.",
        }

    if parsed.scheme.lower() not in SAFE_SCHEMES:
        return {
            "success": False,
            "error": (
                "Only HTTP and HTTPS URLs are allowed."
            ),
        }

    if not parsed.netloc:
        return {
            "success": False,
            "error": "URL must contain a valid host.",
        }

    return None
def validate_browser_element(
    session,
    element_id,
    *,
    require_interactive=True,
    allow_sensitive=False,
):
    """Validate an element against the latest browser state."""

    if session is None:
        return None

    state = session.state

    if not isinstance(state, dict):
        return {
            "success": False,
            "error": "No current browser state is available.",
        }

    dom = state.get("dom") or {}

    for element in dom.get("elements", []):
        if element.get("id") != element_id:
            continue

        if not element.get("visible", False):
            return {
                "success": False,
                "error": f"Element '{element_id}' is not visible.",
            }

        if (
            require_interactive
            and not element.get("interactive", False)
        ):
            return {
                "success": False,
                "error": f"Element '{element_id}' is not interactive.",
            }

        if (
            not allow_sensitive
            and element.get("sensitive", False)
        ):
            return {
                "success": False,
                "error": (
                    f"Element '{element_id}' is sensitive. "
                    "This action is blocked."
                ),
            }

        return None

    return {
        "success": False,
        "error": (
            f"Element '{element_id}' does not exist "
            "in the latest browser state."
        ),
    }