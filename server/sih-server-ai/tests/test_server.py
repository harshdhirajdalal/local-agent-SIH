import asyncio

from fastapi.testclient import TestClient

from server import app, sessions


client = TestClient(app)


def test_health():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_session_creation():
    sessions.sessions.clear()

    response = client.post(
        "/session",
        json={"session_id": "test-session"},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["session_id"] == "test-session"


def test_websocket_connection():
    sessions.sessions.clear()

    session_id = "ws-test-session"

    with client.websocket_connect(
        f"/ws/browser/{session_id}"
    ) as websocket:

        websocket.send_json({
            "type": "ping",
            "session_id": session_id,
        })

        response = websocket.receive_json()

        assert response["type"] == "pong"
        assert response["session_id"] == session_id


def test_websocket_action_roundtrip(monkeypatch):
    sessions.sessions.clear()

    calls = {"count": 0}

    def fake_qwen(messages, tools):
        calls["count"] += 1

        if calls["count"] == 1:
            return {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call-1",
                        "function": {
                            "name": "click",
                            "arguments": {
                                "element_id": "search-button"
                            },
                        },
                    }
                ],
                "_timing": {
                    "qwen_wall_time_seconds": 0.01
                },
            }

        return {
            "role": "assistant",
            "content": "Done.",
            "_timing": {
                "qwen_wall_time_seconds": 0.01
            },
        }

    monkeypatch.setattr(
        "server.call_qwen",
        fake_qwen,
    )

    session_id = "action-test"

    with client.websocket_connect(
        f"/ws/browser/{session_id}"
    ) as websocket:

        # Initial browser state
        websocket.send_json({
            "type": "browser_state",
            "session_id": session_id,
            "page": {
                "url": "https://example.test",
                "title": "Test page",
            },
            "viewport": {
                "width": 1280,
                "height": 720,
                "dpr": 1,
            },
            "dom": {
                "elements": [
                    {
                        "id": "search-button",
                        "type": "button",
                        "label": "Search",
                        "text": "Search",
                        "bbox": {
                            "x": 10,
                            "y": 10,
                            "width": 100,
                            "height": 40,
                        },
                        "visible": True,
                        "interactive": True,
                        "sensitive": False,
                    }
                ]
            },
            "visual": {
                "source": "test",
                "image": None,
                "elements": [],
            },
        })

        # Start task
        websocket.send_json({
            "type": "task",
            "session_id": session_id,
            "request_id": "task-1",
            "user_request": "Click the search button",
        })

        # Receive browser action
        action = websocket.receive_json()

        assert action["type"] == "browser_action"
        assert action["action"] == "click"
        assert (
            action["parameters"]["element_id"]
            == "search-button"
        )

        action_request_id = action["request_id"]

        # ACK the browser action.
        #
        # IMPORTANT:
        # Do NOT send browser_state yet.
        # The server itself will request a fresh state.
        websocket.send_json({
            "type": "action_result",
            "session_id": session_id,
            "request_id": action_request_id,
            "success": True,
            "action": "click",
            "state_changed": True,
        })

        # -------------------------------------------------
        # NEW STATE-SYNC PROTOCOL
        # -------------------------------------------------

        refresh_request = websocket.receive_json()

        assert refresh_request["type"] == (
            "capture_and_sanitize"
        )

        refresh_request_id = refresh_request["request_id"]

        # Respond to THE NEW request ID.
        websocket.send_json({
            "type": "browser_state",
            "session_id": session_id,
            "request_id": refresh_request_id,

            "page": {
                "url": "https://example.test/search",
                "title": "Search results",
            },

            "viewport": {
                "width": 1280,
                "height": 720,
                "dpr": 1,
            },

            "dom": {
                "elements": [
                    {
                        "id": "search-button",
                        "type": "button",
                        "label": "Search",
                        "text": "Search",
                        "bbox": {
                            "x": 10,
                            "y": 10,
                            "width": 100,
                            "height": 40,
                        },
                        "visible": True,
                        "interactive": True,
                        "sensitive": False,
                    },
                    {
                        "id": "search-result",
                        "type": "link",
                        "label": "Search result",
                        "text": "Search result",
                        "bbox": {
                            "x": 10,
                            "y": 100,
                            "width": 300,
                            "height": 40,
                        },
                        "visible": True,
                        "interactive": True,
                        "sensitive": False,
                    },
                ]
            },

            "visual": {
                "source": "test",
                "image": None,
                "elements": [],
            },
        })

        # The second fake model call should now finish.
        result = websocket.receive_json()

        assert result["type"] == "agent_result"
        assert result["session_id"] == session_id
        assert result["success"] is True
        assert result["turns"] == 2
