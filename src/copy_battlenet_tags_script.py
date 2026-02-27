import tkinter as tk
from tkinter import messagebox
import os
import shutil
import threading
import asyncio
import keyboard
import pyperclip
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable
import json
import time
import websockets
from websockets.exceptions import ConnectionClosed

import sys
from game_client_server import GameClientServer

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# --- Context & Data Extraction ---
@dataclass
class Context:
    SOCKET_PAYLOAD: dict[str, Any] = field(default_factory=dict)
    LOBBY_UPDATED: float = 0.0


def get_ordered_lobby_tags(ctx: Context) -> list[str]:
    rec_message = ctx.SOCKET_PAYLOAD.get("GameLobbySetup")
    if not rec_message:
        return []

    # Using dictionary get/getattr to safely handle dicts or objects
    payload = (
        getattr(rec_message, "payload", rec_message.get("payload"))
        if isinstance(rec_message, dict)
        else rec_message.payload
    )
    lobby_players = (
        getattr(payload, "players", payload.get("players", []))
        if isinstance(payload, dict)
        else payload.players
    )

    def player_filter(player):
        p_dict = player if isinstance(player, dict) else player.__dict__
        return (
            p_dict.get("slotStatus", 0) == 2
            and p_dict.get("slotType", -1) == 0
            and p_dict.get("team", -1) in (0, 1)
            and not p_dict.get("isObserver", True)
        )

    filtered_lobby_players = list(filter(player_filter, lobby_players))

    tags = []
    for player in filtered_lobby_players:
        p_dict = player if isinstance(player, dict) else player.__dict__
        tag = p_dict.get("battletag") or p_dict.get("name")
        if tag:
            tags.append(tag)

    return tags


def copy_tags_to_clipboard(ctx: Context, delimiter: str):
    tags = get_ordered_lobby_tags(ctx)
    if not tags:
        logger.info("No players found to copy.")
        return

    clipboard_string = delimiter.join(tags)
    pyperclip.copy(clipboard_string)
    logger.info(f"Copied {len(tags)} tags to clipboard: '{clipboard_string}'")


# --- Socket Service ---
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
        self.register_handler(self._core_context_handler)

    def register_handler(self, fn: Callable[[Any, Any], Awaitable[None]]) -> None:
        self.response_handlers.append(fn)

    async def _core_context_handler(self, message: Any, websocket: Any) -> None:
        msg_type = (
            message.get("messageType", "")
            if isinstance(message, dict)
            else getattr(message, "messageType", "")
        )
        if msg_type == "GameLobbySetup":
            self.context.LOBBY_UPDATED = time.monotonic()
        elif msg_type == "SetGlueScreen":
            logger.info("[SETGLUESCREEN] Transitioned")

    async def __aenter__(self):
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run())
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._stop_event.set()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _run(self):
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
                            msg_type = data.get("messageType")
                            self.context.SOCKET_PAYLOAD[msg_type] = data

                            tasks = [
                                handler(data, websocket)
                                for handler in self.response_handlers
                            ]
                            if tasks:
                                await asyncio.gather(*tasks)
                        except json.JSONDecodeError:
                            pass
            except (ConnectionClosed, OSError):
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[SocketService] Exception: {e}")
                await asyncio.sleep(1)


# --- Async Background Task Runner ---
async def start_async_service(
    hotkey: str, delimiter: str, shutdown_event: asyncio.Event
):
    """Runs the socket and hotkey listener until shutdown_event is set."""
    app_context = Context()

    try:
        keyboard.add_hotkey(
            hotkey, lambda: copy_tags_to_clipboard(app_context, delimiter)
        )
        logger.info(f"Registered hotkey: {hotkey}")
    except ValueError as e:
        logger.error(f"Failed to bind hotkey: {e}")
        return

    establish_msg = {"messageType": "appClient"}
    async with SocketService("ws://127.0.0.1:8888", establish_msg, app_context):
        try:
            # Wait here until the UI thread sets the event
            await shutdown_event.wait()
            logger.info("Shutdown event received. Closing service...")
        except asyncio.CancelledError:
            pass
        finally:
            keyboard.unhook_all()
            logger.info("Hotkeys unhooked.")


# --- Tkinter UI ---
class AppUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("WC3 BattleTag Copier")
        self.geometry("500x250")
        self.resizable(False, False)

        # UI State Variables
        self.is_running = False
        self.loop = None
        self.service_thread = None
        self.shutdown_event = None

        # Config Variables
        self.delimiter_var = tk.StringVar(value=" ")
        self.hotkey_var = tk.StringVar(value="ctrl+shift+c")
        self.webui_var = tk.StringVar(
            value=r"C:\Program Files (x86)\Warcraft III\_retail_\webui"
        )

        self._build_grid()

    def _build_grid(self):
        padding = {"padx": 10, "pady": 10}

        tk.Label(self, text="Delimiter String:").grid(
            row=0, column=0, sticky="e", **padding
        )
        tk.Entry(self, textvariable=self.delimiter_var, width=40).grid(
            row=0, column=1, **padding
        )

        tk.Label(self, text="Copy Hotkey:").grid(row=1, column=0, sticky="e", **padding)
        tk.Entry(self, textvariable=self.hotkey_var, width=40).grid(
            row=1, column=1, **padding
        )

        tk.Label(self, text="WebUI Directory:").grid(
            row=2, column=0, sticky="e", **padding
        )
        tk.Entry(self, textvariable=self.webui_var, width=40).grid(
            row=2, column=1, **padding
        )

        # The Toggle Button
        self.toggle_btn = tk.Button(
            self,
            text="Start Service",
            command=self.toggle_service,
            width=20,
            bg="#4CAF50",
            fg="white",
        )
        self.toggle_btn.grid(row=3, column=0, columnspan=2, pady=20)

    def toggle_service(self):
        """Toggles the background service on and off."""
        if self.is_running:
            self.stop_service()
        else:
            self.start_service()

    def start_service(self):
        """Copies the webui file and spawns the background thread."""
        webui_dir = self.webui_var.get()
        target_file = os.path.join(webui_dir, "index.js")
        local_file = "index.js"

        if os.path.exists(local_file):
            try:
                os.makedirs(webui_dir, exist_ok=True)
                shutil.copyfile(local_file, target_file)
                logger.info(f"Copied {local_file} to {target_file}")
            except PermissionError:
                messagebox.showerror(
                    "Permission Error",
                    f"Cannot write to {webui_dir}.\nPlease run as Administrator.",
                )
                return
            except Exception as e:
                messagebox.showerror("Error", f"Failed to copy index.js: {e}")
                return
        else:
            logger.warning("Local 'index.js' not found. Skipping file copy.")

        # Update UI state
        self.is_running = True
        self.toggle_btn.config(text="Stop Service", bg="#f44336")

        # Start the background thread
        self.service_thread = threading.Thread(
            target=self.run_asyncio_loop, daemon=True
        )
        self.service_thread.start()

    def stop_service(self):
        """Signals the background asyncio loop to shut down."""
        if self.loop and self.loop.is_running() and self.shutdown_event:
            # Safely trigger the event inside the running asyncio loop
            self.loop.call_soon_threadsafe(self.shutdown_event.set)

        # Update UI state
        self.is_running = False
        self.toggle_btn.config(text="Start Service", bg="#4CAF50")

    def run_asyncio_loop(self):
        """Worker function containing the isolated asyncio event loop."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        delimiter = self.delimiter_var.get()
        hotkey = self.hotkey_var.get()
        self.shutdown_event = asyncio.Event()

        # Instantiate the Relay Server from game_client_server.py
        relay_server = GameClientServer(host="127.0.0.1", port=8888)

        async def run_all():
            # Start the relay server tasks
            server_task = self.loop.create_task(relay_server.start_server())
            queue_task = self.loop.create_task(relay_server.process_message_queue())

            # Start the app client task and wait for shutdown
            await start_async_service(hotkey, delimiter, self.shutdown_event)

            # Teardown the relay server when the UI signals a stop
            server_task.cancel()
            queue_task.cancel()

        try:
            self.loop.run_until_complete(run_all())
        finally:
            self.loop.close()
            logger.info("Asyncio loop closed.")

    def resource_path(self, relative_path):
        """ Get absolute path to resource, works for dev and for PyInstaller """
        try:
            # PyInstaller creates a temp folder and stores path in _MEIPASS
            base_path = sys._MEIPASS
        except AttributeError:
            base_path = os.path.abspath(".")
        return os.path.join(base_path, relative_path)

    def start_service(self):
        """Copies the webui file and spawns the background thread."""
        webui_dir = self.webui_var.get()
        target_file = os.path.join(webui_dir, "index.js")

        # Use resource_path to find index.js whether running as .py or .exe
        local_file = self.resource_path("index.js")

        if os.path.exists(local_file):
            try:
                os.makedirs(webui_dir, exist_ok=True)
                shutil.copyfile(local_file, target_file)
                logger.info(f"Copied {local_file} to {target_file}")
            except PermissionError:
                messagebox.showerror("Permission Error", f"Cannot write to {webui_dir}.\nPlease run as Administrator.")
                return
            except Exception as e:
                messagebox.showerror("Error", f"Failed to copy index.js: {e}")
                return
        else:
            logger.warning(f"Local '{local_file}' not found. Skipping file copy.")

        # Update UI state
        self.is_running = True
        self.toggle_btn.config(text="Stop Service", bg="#f44336")

        # Start the background thread
        self.service_thread = threading.Thread(target=self.run_asyncio_loop, daemon=True)
        self.service_thread.start()


if __name__ == "__main__":
    app = AppUI()
    app.mainloop()
