"""Deprecated compatibility module.

The production architecture does NOT make the server a WebSocket client.
The browser extension connects to the FastAPI server, which owns the
server-side WebSocket connection.

Use transport.sessions.BrowserSession for server-side browser communication.
"""


class BrowserClient:
    """Compatibility stub for the old server-as-client design.

    This class intentionally cannot connect. It remains only so older imports
    fail with a useful message instead of silently creating the wrong topology.
    """

    def __init__(self, *args, **kwargs):
        raise RuntimeError(
            "BrowserClient is deprecated. The browser extension must connect "
            "to FastAPI via /ws/browser/{session_id}. Use BrowserSession."
        )
