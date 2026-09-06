"""Browser session and connection management."""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from fastapi import WebSocket

from agent.controller import AgentController
from tools.browser_actions import register_tools as register_browser_tools
from tools.browser_state import register_tools as register_state_tools
from tools.registry import ToolRegistry
from tools.web import register_tools as register_web_tools


@dataclass
class BrowserSession:
    """All state belonging to one connected browser agent."""

    session_id: str
    websocket: Optional[WebSocket] = None
    state: Optional[dict[str, Any]] = None
    user_request: Optional[str] = None
    step_id: Optional[str] = None
    messages: list[dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    last_state_at: Optional[float] = None
    loop: Optional[asyncio.AbstractEventLoop] = None
    connected: bool = False
    agent_task: Optional[asyncio.Task] = None

    # Filled during initialization after the object exists.
    registry: ToolRegistry = field(init=False)
    controller: AgentController = field(init=False)

    # request_id -> Future used by synchronous browser-action tools.
    pending_requests: dict[str, asyncio.Future] = field(default_factory=dict)

    def __post_init__(self):
        self.registry = ToolRegistry()

        # These registrations are session-bound. The same tool names
        # are used, but each handler reads/sends through this session.
        register_state_tools(self.registry, session=self)
        register_browser_tools(self.registry, session=self)
        register_web_tools(self.registry)

        from config import MAX_AGENT_TURNS

        self.controller = AgentController(
            registry=self.registry,
            max_turns=MAX_AGENT_TURNS,
            state_refresh=self.refresh_state_sync,
        )

    def update_state(self, state: dict[str, Any]) -> None:
        """Replace the latest browser state snapshot."""

        self.state = state
        self.last_state_at = time.time()

    async def send_json(self, message: dict[str, Any]) -> None:
        if self.websocket is None or not self.connected:
            raise RuntimeError("Browser WebSocket is not connected.")

        await self.websocket.send_json(message)

    async def send_command(
        self,
        action: str,
        parameters: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Send an action to the extension and wait for its ACK."""

        if self.websocket is None or not self.connected:
            raise RuntimeError("Browser WebSocket is not connected.")

        from config import ACTION_TIMEOUT

        request_id = str(uuid.uuid4())
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        self.pending_requests[request_id] = future

        message = {
            "type": "browser_action",
            "session_id": self.session_id,
            "request_id": request_id,
            "step_id": self.step_id,
            "action": action,
            "parameters": parameters or {},
        }

        try:
            await self.websocket.send_json(message)
            return await asyncio.wait_for(
                future,
                timeout=ACTION_TIMEOUT,
            )
        finally:
            self.pending_requests.pop(request_id, None)

    def send_command_sync(
        self,
        action: str,
        parameters: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Thread-safe synchronous bridge for existing tool handlers."""

        if self.loop is None:
            raise RuntimeError("Session event loop is not available.")

        future = asyncio.run_coroutine_threadsafe(
            self.send_command(action, parameters),
            self.loop,
        )

        # The timeout is enforced inside send_command as well. This
        # outer result() simply blocks the worker thread until completion.
        return future.result()

    async def request_state(self) -> dict[str, Any]:
        """Request a fresh sanitized browser state from the extension."""

        if self.websocket is None or not self.connected:
            raise RuntimeError("Browser WebSocket is not connected.")

        from config import ACTION_TIMEOUT

        request_id = str(uuid.uuid4())
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        self.pending_requests[request_id] = future

        try:
            await self.websocket.send_json({
                "type": "capture_and_sanitize",
                "session_id": self.session_id,
                "request_id": request_id,
            })

            return await asyncio.wait_for(
                future,
                timeout=ACTION_TIMEOUT,
            )
        finally:
            self.pending_requests.pop(request_id, None)

    def request_state_sync(self) -> dict[str, Any]:
        """Thread-safe synchronous bridge for a state refresh."""

        if self.loop is None:
            raise RuntimeError("Session event loop is not available.")

        future = asyncio.run_coroutine_threadsafe(
            self.request_state(),
            self.loop,
        )

        # The timeout is enforced by request_state().
        return future.result()

    def refresh_state_sync(self) -> dict[str, Any]:
        """Refresh live state and return only compact model-safe context."""

        self.request_state_sync()

        page_info = self.registry.execute(
            "get_page_info",
            {},
        )

        interactive_elements = self.registry.execute(
            "get_interactive_elements",
            {},
        )

        return {
            "page": page_info,
            "interactive_elements": interactive_elements,
        }

    def resolve_request(self, message: dict[str, Any]) -> bool:
        """Resolve a pending action/state request from an extension message."""

        request_id = message.get("request_id")
        if not request_id:
            return False

        future = self.pending_requests.get(request_id)
        if future is None or future.done():
            return False

        future.set_result(message)
        return True

    def fail_pending_requests(self, error: str) -> None:
        """Wake all waiting tool calls when the browser disconnects."""

        for future in list(self.pending_requests.values()):
            if not future.done():
                future.set_exception(RuntimeError(error))

        self.pending_requests.clear()

    def summary(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "connected": self.connected,
            "has_browser_state": self.state is not None,
            "has_user_request": self.user_request is not None,
            "step_id": self.step_id,
            "created_at": self.created_at,
            "last_state_at": self.last_state_at,
        }


class SessionManager:
    """In-memory manager for multiple browser sessions."""

    def __init__(self):
        self.sessions: dict[str, BrowserSession] = {}
        self.lock = asyncio.Lock()

    async def create_session(
        self,
        session_id: Optional[str] = None,
    ) -> BrowserSession:
        async with self.lock:
            session_id = session_id or str(uuid.uuid4())

            if session_id in self.sessions:
                raise ValueError(
                    f"Session '{session_id}' already exists."
                )

            session = BrowserSession(session_id=session_id)
            self.sessions[session_id] = session
            return session

    async def get_or_create(
        self,
        session_id: str,
    ) -> BrowserSession:
        async with self.lock:
            session = self.sessions.get(session_id)
            if session is not None:
                return session

            session = BrowserSession(session_id=session_id)
            self.sessions[session_id] = session
            return session

    def get(self, session_id: str) -> Optional[BrowserSession]:
        return self.sessions.get(session_id)

    async def remove(self, session_id: str) -> None:
        async with self.lock:
            session = self.sessions.pop(session_id, None)

        if session is not None:
            session.connected = False
            session.fail_pending_requests(
                "Browser session was removed."
            )

            if (
                session.agent_task is not None
                and not session.agent_task.done()
            ):
                session.agent_task.cancel()

    def summaries(self) -> list[dict[str, Any]]:
        return [
            session.summary()
            for session in self.sessions.values()
        ]
