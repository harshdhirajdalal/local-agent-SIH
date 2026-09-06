"""FastAPI/WebSocket server for the SIH26171 browser agent."""

from __future__ import annotations

import asyncio
import threading
import time
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from config import (
    HOST,
    LOG_TIMINGS,
    MODEL,
    OLLAMA_MAX_CONCURRENT,
    PORT,
)
from main import SYSTEM_PROMPT, call_qwen
from transport.sessions import BrowserSession, SessionManager


app = FastAPI(
    title="SIH26171 Server AI",
    version="0.1.0",
)

sessions = SessionManager()
ollama_semaphore = threading.BoundedSemaphore(OLLAMA_MAX_CONCURRENT)


async def build_initial_context(session: BrowserSession) -> dict[str, Any]:
    """Build compact model context from the current live browser state."""

    try:
        page_info = session.registry.execute(
            "get_page_info",
            {},
        )

        interactive_elements = session.registry.execute(
            "get_interactive_elements",
            {},
        )

        return {
            "page": page_info,
            "interactive_elements": interactive_elements,
        }

    except Exception as error:
        return {
            "error": str(error),
        }


def model_call_with_queue(messages, tools):
    """Run one Ollama request through the global concurrency limiter."""

    queue_start = time.perf_counter()

    with ollama_semaphore:
        queue_wait = time.perf_counter() - queue_start
        message = call_qwen(messages, tools)
        message.setdefault("_timing", {})[
            "queue_wait_seconds"
        ] = queue_wait
        return message


async def run_session_agent(session: BrowserSession) -> None:
    """Run the agent for one session without blocking the WebSocket receiver."""

    if not session.user_request:
        return

    if session.state is None:
        try:
            await session.send_json({
                "type": "error",
                "session_id": session.session_id,
                "error": "No browser state is available yet.",
            })
        except Exception:
            pass
        return

    initial_context = await build_initial_context(session)

    session.messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        },
        {
            "role": "system",
            "content": (
                "CURRENT BROWSER STATE:\n"
                + str(initial_context)
            ),
        },
        {
            "role": "user",
            "content": session.user_request,
        },
    ]

    agent_start = time.perf_counter()

    print("\n" + "=" * 60)
    print(f"AGENT RUN [{session.session_id}]")
    print("=" * 60)

    try:
        result = await asyncio.to_thread(
            session.controller.run,
            session.messages,
            model_call_with_queue,
        )
    except asyncio.CancelledError:
        raise
    except Exception as error:
        print(
            f"[Server] Agent failed for {session.session_id}: {error}"
        )
        try:
            await session.send_json({
                "type": "error",
                "session_id": session.session_id,
                "error": str(error),
            })
        except Exception:
            pass
        return

    elapsed = time.perf_counter() - agent_start

    # Keep the current result available for inspection.
    session.messages = result.get("messages", session.messages)

    final_message = result.get("final_message", {})

    try:
        await session.send_json({
            "type": "agent_result",
            "session_id": session.session_id,
            "success": "error" not in result,
            "turns": result.get("turns"),
            "message": {
                "role": final_message.get("role", "assistant"),
                "content": final_message.get("content", ""),
            },
            "error": result.get("error"),
        })
    except Exception:
        pass

    if LOG_TIMINGS:
        model_times = []
        queue_times = []

        for message in session.messages:
            if message.get("role") != "assistant":
                continue

            timing = message.get("_timing", {})
            if timing.get("model_wall_time_seconds") is not None:
                model_times.append(
                    timing["model_wall_time_seconds"]
                )
            if timing.get("queue_wait_seconds") is not None:
                queue_times.append(
                    timing["queue_wait_seconds"]
                )

        print("\n" + "-" * 60)
        print(f"TIMING SUMMARY [{session.session_id}]")
        print("-" * 60)
        print(f"Total agent time: {elapsed:.3f} s")
        print(
            f"Model turns: "
            f"{result.get('turns', '?')}"
        )

        if model_times:
            print(
                f"Total model time: "
                f"{sum(model_times):.3f} s"
            )
            print(
                f"Average model time/cycle: "
                f"{sum(model_times) / len(model_times):.3f} s"
            )
            print(
                f"Fastest model cycle: "
                f"{min(model_times):.3f} s"
            )
            print(
                f"Slowest model cycle: "
                f"{max(model_times):.3f} s"
            )

            for index, value in enumerate(model_times, start=1):
                print(
                    f"Model cycle {index}: {value:.3f} s"
                )

        if queue_times:
            print(
                f"Total Ollama queue wait: "
                f"{sum(queue_times):.3f} s"
            )

        print("-" * 60)


async def handle_browser_message(
    session: BrowserSession,
    message: dict[str, Any],
) -> None:
    """Handle one JSON message from the browser extension."""

    message_type = message.get("type")

    if message_type == "browser_state":
        session.update_state(message)
        print(
            f"[WS] State received for {session.session_id}"
        )

        # A browser_state can also be the response to an explicit
        # capture_and_sanitize/state-refresh request.
        if message.get("request_id"):
            session.resolve_request(message)

        # If a task was waiting for initial browser state, start it now.
        if (
            session.user_request
            and (
                session.agent_task is None
                or session.agent_task.done()
            )
        ):
            session.agent_task = asyncio.create_task(
                run_session_agent(session)
            )
        return

    if message_type == "task":
        request = message.get("user_request")

        if not isinstance(request, str) or not request.strip():
            await session.send_json({
                "type": "error",
                "session_id": session.session_id,
                "error": "Task message requires a non-empty user_request.",
            })
            return

        if (
            session.agent_task is not None
            and not session.agent_task.done()
        ):
            await session.send_json({
                "type": "error",
                "session_id": session.session_id,
                "error": "A task is already running for this session.",
            })
            return

        session.user_request = request.strip()
        session.step_id = message.get("step_id")

        if session.state is None:
            # Ask the extension to capture a fresh sanitized state.
            await session.send_json({
                "type": "capture_and_sanitize",
                "session_id": session.session_id,
                "request_id": message.get("request_id"),
            })
            print(
                f"[WS] Requested fresh state for {session.session_id}"
            )
        else:
            session.agent_task = asyncio.create_task(
                run_session_agent(session)
            )

        return

    if message_type == "action_result":
        resolved = session.resolve_request(message)
        if not resolved:
            print(
                f"[WS] Unmatched action_result for "
                f"{session.session_id}: {message.get('request_id')}"
            )
        else:
            print(
                f"[WS] Action ACK [{session.session_id}] "
                f"{message.get('action')} -> "
                f"{'OK' if message.get('success') else 'ERROR'}"
            )
        return

    # Optional support for a state response using request_id.
    if message_type == "state_result":
        session.resolve_request(message)
        return

    if message_type == "ping":
        await session.send_json({
            "type": "pong",
            "session_id": session.session_id,
        })
        return

    await session.send_json({
        "type": "error",
        "session_id": session.session_id,
        "error": f"Unknown message type: {message_type}",
    })


@app.get("/health")
async def health():
    """Basic health endpoint."""

    return {
        "status": "ok",
        "model": MODEL,
        "sessions": len(sessions.sessions),
        "ollama_max_concurrent": OLLAMA_MAX_CONCURRENT,
    }

from pydantic import BaseModel
from fastapi import HTTPException

class CreateSessionRequest(BaseModel):
    session_id: str | None = None
    
@app.post("/session")
async def create_session(request: CreateSessionRequest | None = None):
    """Create a browser session."""

    requested_id = request.session_id if request else None

    try:
        session = await sessions.create_session(requested_id)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error))

    return {
        "session_id": session.session_id,
    }


@app.get("/sessions")
async def list_sessions():
    """Development endpoint listing active sessions."""

    return {
        "sessions": sessions.summaries(),
    }


@app.websocket("/ws/browser/{session_id}")
async def browser_websocket(
    websocket: WebSocket,
    session_id: str,
):
    """Persistent WebSocket endpoint used by browser extensions."""

    session = await sessions.get_or_create(session_id)

    # Reject a second simultaneous browser connection for the same session.
    if session.connected:
        await websocket.close(code=1008, reason="Session already connected")
        return

    await websocket.accept()

    session.websocket = websocket
    session.loop = asyncio.get_running_loop()
    session.connected = True

    print(
        f"[WS] Browser connected: {session_id}"
    )

    try:
        while True:
            message = await websocket.receive_json()

            if not isinstance(message, dict):
                await websocket.send_json({
                    "type": "error",
                    "session_id": session_id,
                    "error": "WebSocket message must be a JSON object.",
                })
                continue

            # Ignore accidental cross-session messages.
            incoming_session = message.get("session_id")
            if (
                incoming_session is not None
                and incoming_session != session_id
            ):
                await websocket.send_json({
                    "type": "error",
                    "session_id": session_id,
                    "error": "session_id does not match WebSocket session.",
                })
                continue

            await handle_browser_message(
                session,
                message,
            )

    except WebSocketDisconnect:
        print(
            f"[WS] Browser disconnected: {session_id}"
        )
    except Exception as error:
        print(
            f"[WS] Connection error [{session_id}]: {error}"
        )
    finally:
        session.connected = False
        session.websocket = None
        session.fail_pending_requests(
            "Browser WebSocket disconnected."
        )

        if (
            session.agent_task is not None
            and not session.agent_task.done()
        ):
            session.agent_task.cancel()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "server:app",
        host=HOST,
        port=PORT,
        reload=False,
    )
