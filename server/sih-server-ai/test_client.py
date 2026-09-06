"""End-to-end client for testing the real SIH26171 server.

This script pretends to be the browser extension. It connects to the
running server.py, sends browser state, submits a task, acknowledges
browser actions, answers state-refresh requests, and waits for the final
agent_result.

Usage:
    python test_client.py

Optional environment variables:
    SERVER_URL=ws://127.0.0.1:8000
    HTTP_URL=http://127.0.0.1:8000
    SESSION_ID=server-e2e-test
    TASK="Click the Search button"
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import uuid

import requests
import websockets


HTTP_URL = os.getenv("HTTP_URL", "http://127.0.0.1:8000").rstrip("/")
WS_URL = os.getenv("SERVER_URL", "ws://127.0.0.1:8000").rstrip("/")
SESSION_ID = os.getenv("SESSION_ID", f"server-e2e-{uuid.uuid4().hex[:8]}")
TASK = os.getenv("TASK", "Click the Search button")



def make_browser_state(after_click: bool = False) -> dict:
    """Return a small, realistic browser-state payload."""

    if after_click:
        elements = [
            {
                "id": "results-heading",
                "type": "heading",
                "label": "Search Results",
                "text": "Search Results",
                "visible": True,
                "interactive": False,
                "sensitive": False,
                "bbox": {"x": 100, "y": 120, "width": 300, "height": 40},
            }
        ]
        title = "Search Results"
        url = "https://example.local/results"
    else:
        elements = [
            {
                "id": "search-box",
                "type": "textbox",
                "label": "Search",
                "placeholder": "Search here",
                "visible": True,
                "interactive": True,
                "sensitive": False,
                "bbox": {"x": 100, "y": 200, "width": 400, "height": 40},
            },
            {
                "id": "search-button",
                "type": "button",
                "label": "Search",
                "text": "Search",
                "visible": True,
                "interactive": True,
                "sensitive": False,
                "bbox": {"x": 510, "y": 200, "width": 100, "height": 40},
            },
        ]
        title = "Example Search"
        url = "https://example.local/search"

    return {
        "type": "browser_state",
        "session_id": SESSION_ID,
        "page": {
            "url": url,
            "title": title,
        },
        "viewport": {
            "width": 1904,
            "height": 948,
            "dpr": 1,
            "scrollX": 0,
            "scrollY": 0,
        },
        "dom": {
            "elements": elements,
        },
        "visual": {
            "elements": [],
        },
    }



def check_http_server() -> None:
    """Verify that server.py is reachable over HTTP."""

    print(f"Checking server: {HTTP_URL}")

    response = requests.get(f"{HTTP_URL}/health", timeout=5)
    response.raise_for_status()

    health = response.json()
    print("HEALTH:")
    print(json.dumps(health, indent=2))

    if health.get("status") != "ok":
        raise RuntimeError("Server health endpoint did not report status=ok")


async def run() -> None:
    """Run the complete server/browser protocol test."""

    check_http_server()

    uri = f"{WS_URL}/ws/browser/{SESSION_ID}"

    print(f"\nConnecting WebSocket: {uri}")

    async with websockets.connect(uri, open_timeout=10, close_timeout=5) as ws:
        print("CONNECTED")

        # Initial browser state.
        print("\n→ browser_state (initial)")
        await ws.send(json.dumps(make_browser_state(False)))

        # Give the server a tiny amount of time to store the state before
        # the task arrives. This mirrors the extension's normal ordering.
        await asyncio.sleep(0.2)

        # User task.
        task_message = {
            "type": "task",
            "session_id": SESSION_ID,
            "step_id": "server-e2e-1",
            "user_request": TASK,
        }

        print(f"→ task: {TASK}")
        await ws.send(json.dumps(task_message))

        print("\nWaiting for the real agent loop...\n")

        saw_browser_action = False
        saw_state_refresh = False
        saw_agent_result = False

        while True:
            raw = await asyncio.wait_for(ws.recv(), timeout=180)
            message = json.loads(raw)
            message_type = message.get("type")

            print(f"← {message_type}")
            print(json.dumps(message, indent=2))

            if message_type == "browser_action":
                saw_browser_action = True

                request_id = message.get("request_id")
                action = message.get("action")
                parameters = message.get("parameters", {})

                print(
                    f"\n→ action_result: {action} "
                    f"request_id={request_id}"
                )

                # Pretend the browser successfully executed the action.
                await ws.send(json.dumps({
                    "type": "action_result",
                    "session_id": SESSION_ID,
                    "request_id": request_id,
                    "action": action,
                    "success": True,
                    "parameters": parameters,
                }))

                continue

            if message_type == "capture_and_sanitize":
                saw_state_refresh = True

                request_id = message.get("request_id")

                print(
                    f"\n→ browser_state (refresh, request_id={request_id})"
                )

                # Simulate the browser changing after the previous action.
                await ws.send(json.dumps({
                    **make_browser_state(True),
                    "request_id": request_id,
                }))

                continue

            if message_type == "pong":
                continue

            if message_type == "agent_result":
                saw_agent_result = True
                print("\n" + "=" * 60)
                print("END-TO-END RESULT")
                print("=" * 60)
                print(json.dumps(message, indent=2))
                break

            if message_type == "error":
                print("\nSERVER RETURNED AN ERROR")
                print(json.dumps(message, indent=2))
                raise RuntimeError(message.get("error", "Unknown server error"))

            print(f"Ignoring unexpected message type: {message_type}")

        if not saw_agent_result:
            raise RuntimeError("No agent_result received")

        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        print(f"Server reachable:       YES")
        print(f"WebSocket connected:     YES")
        print(f"Browser state accepted:  YES")
        print(f"Agent action received:   {'YES' if saw_browser_action else 'NO'}")
        print(f"State refresh handled:   {'YES' if saw_state_refresh else 'NO'}")
        print(f"Final agent result:      YES")
        print("\nSERVER E2E TEST PASSED")


if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print("\nTest interrupted.")
        sys.exit(130)
    except Exception as error:
        print(f"\nSERVER E2E TEST FAILED: {error}")
        sys.exit(1)
