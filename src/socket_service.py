import asyncio
from dataclasses import dataclass, field
import json
import time
import logging
from typing import Callable, Awaitable, Any
import websockets
from websockets.exceptions import ConnectionClosed
from pydantic import ValidationError
from typing import Any, Literal

from payloads.receive_payloads import RecMessage



# Assuming Context, RecMessage, ValidationAdvisor are imported appropriately
logger = logging.getLogger(__name__)


@dataclass
class Context:
    PROCESS_FOCUSED: str | int | None = None
    PROCESS_OPENED: str | int | None = None
    PROCESS_CLOSED: str | int | None = None
    PROCESS_RUNNING: str | int | None = None
    SLEPT_FOR: int | float | None = None
    SOCKET_PAYLOAD: dict[str, RecMessage] = field(default_factory=dict)
    CURRENT_STEP: int = 0
    DIR_EVENT: Literal["CREATED", "MODIFIED", "DELETED", "MOVED"] | None = None
    LOBBY_UPDATED: float = time.monotonic()
    LOBBY_DODGERS: set[str] = field(default_factory=set)

    def clear(self):
        self.PROCESS_FOCUSED = None
        self.PROCESS_OPENED = None
        self.PROCESS_CLOSED = None
        self.SLEPT_FOR = None
        self.SOCKET_PAYLOAD.clear()
        self.CURRENT_STEP = 0
        self.DIR_EVENT = None
        self.LOBBY_UPDATED = time.monotonic()
        self.LOBBY_DODGERS = set()


class SocketService:
    def __init__(
        self, server_url: str, establish_message: dict[str, str], context: Context
    ):
        self.server_url = server_url
        self.establish_message = establish_message
        self.context = context
        self._task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()
        self.response_handlers: list[Callable[[Any, Any], Awaitable[None]]] = []

        # Register core contextual handlers here instead of inside the loop
        self.register_handler(self._core_context_handler)

    def register_handler(self, fn: Callable[[Any, Any], Awaitable[None]]) -> None:
        self.response_handlers.append(fn)

    async def _core_context_handler(self, message: Any, websocket: Any) -> None:
        """Handles core context updates, decoupling them from the network loop."""
        if message.messageType == "GameLobbySetup":
            self.context.LOBBY_UPDATED = time.monotonic()
        elif message.messageType == "SetGlueScreen":
            logger.info(f"[SETGLUESCREEN] {message.payload.screen}")

    async def __aenter__(self):
        """Start the socket listener as a background task."""
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run())
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Stop the socket listener gracefully."""
        self._stop_event.set()
        if self._task:
            self._task.cancel()  # Force unblock the socket's async for loop
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None

    async def _run(self):
        """Background loop that maintains connection and updates context."""
        while not self._stop_event.is_set():
            try:
                async with websockets.connect(self.server_url) as websocket:
                    await websocket.send(json.dumps(self.establish_message))
                    logger.info(f"[SocketService] Connected to {self.server_url}")

                    async for msg in websocket:
                        if self._stop_event.is_set():
                            break
                        try:
                            data = json.loads(msg)
                            message = RecMessage(**data)
                            self.context.SOCKET_PAYLOAD[message.messageType] = message

                            # Fire and forget handlers or gather them (gather prevents one slow handler from lagging the socket)
                            tasks = [
                                handler(message, websocket)
                                for handler in self.response_handlers
                            ]
                            if tasks:
                                await asyncio.gather(*tasks)

                        except json.JSONDecodeError:
                            logger.warning(f"Received non-JSON message: {msg}")
                        except ValidationError as e:
                            # Ensuring data is bound before passing to advisor
                            advisor = ValidationAdvisor.from_exception(e, data)
                            advisor.pretty_print()

            except (ConnectionClosed, OSError) as e:
                logger.warning(
                    f"[SocketService] Connection dropped/failed: {e}. Reconnecting in 1s..."
                )
            except asyncio.CancelledError:
                logger.info("[SocketService] Task cancelled. Shutting down loop.")
                break
            except Exception as e:
                logger.error(f"[SocketService] Unexpected error: {e}", exc_info=True)

            # Small delay to prevent tight reconnect loop
            await asyncio.sleep(1)
