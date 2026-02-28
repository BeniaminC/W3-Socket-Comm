import tkinter as tk
from tkinter import messagebox
import os
import shutil
import threading
import asyncio
import keyboard
import pyperclip
import logging
import json
import time
import winreg
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable
import websockets
from websockets.exceptions import ConnectionClosed
import sys
from game_client_server import GameClientServer

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)



def enable_webui_in_registry(enable: bool = True) -> bool:
    """Mirrors setup.ts to allow the Warcraft III client to load local webui files."""
    try:
        # Target: HKCU\SOFTWARE\Blizzard Entertainment\Warcraft III
        key = winreg.CreateKey(
            winreg.HKEY_CURRENT_USER, r"SOFTWARE\Blizzard Entertainment\Warcraft III"
        )
        winreg.SetValueEx(
            key, "Allow Local Files", 0, winreg.REG_DWORD, 1 if enable else 0
        )
        winreg.CloseKey(key)
        logger.info(f"Registry 'Allow Local Files' set to {enable}")
        return True
    except Exception as e:
        logger.error(f"Failed to modify registry: {e}")
        return False


def get_warcraft_install_location() -> str:
    """Mirrors setup.ts to find the installation directory via Registry."""
    reg_install_key = (
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\Warcraft III"
    )
    backup_reg_install_key = (
        r"SOFTWARE\WOW6432Node\Blizzard Entertainment\Warcraft III\Capabilities"
    )

    # Try primary uninstaller key
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_install_key)
        loc, _ = winreg.QueryValueEx(key, "InstallLocation")
        winreg.CloseKey(key)
        if loc:
            return str(loc)
    except OSError:
        pass

    # Try backup capabilities key
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, backup_reg_install_key)
        app_icon, _ = winreg.QueryValueEx(key, "ApplicationIcon")
        winreg.CloseKey(key)
        if app_icon:
            # app_icon is typically: "C:\Program Files (x86)\Warcraft III\_retail_\x86_64\Warcraft III.exe"
            # We move up 3 directories to get the base install path safely without string slicing
            base_path = str(app_icon).strip('"')
            return os.path.dirname(os.path.dirname(os.path.dirname(base_path)))
    except OSError:
        pass

    # Fallback if both fail
    return r"C:\Program Files (x86)\Warcraft III"


@dataclass
class Context:
    SOCKET_PAYLOAD: dict[str, Any] = field(default_factory=dict)
    LOBBY_UPDATED: float = 0.0


def get_ordered_lobby_tags(ctx: Context) -> list[str]:
    rec_message = ctx.SOCKET_PAYLOAD.get("GameLobbySetup")
    if not rec_message:
        return []

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


async def start_async_service(
    hotkey: str, delimiter: str, shutdown_event: asyncio.Event
):
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
            await shutdown_event.wait()
            logger.info("Shutdown event received. Closing service...")
        except asyncio.CancelledError:
            pass
        finally:
            keyboard.unhook_all()
            logger.info("Hotkeys unhooked.")


class AppUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("WC3 BattleTag Copier")
        self.geometry("550x300") # Slightly increased height for the new checkbox
        self.resizable(False, False)

        self.is_running = False
        self.loop = None
        self.service_thread = None
        self.shutdown_event = None

        # Fetch Registry paths
        default_install_dir = get_warcraft_install_location()
        default_webui_dir = os.path.join(default_install_dir, "_retail_", "webui")

        self.delimiter_var = tk.StringVar(value=" ")
        self.hotkey_var = tk.StringVar(value="ctrl+shift+c")
        self.webui_var = tk.StringVar(value=default_webui_dir)

        self.startup_var = tk.BooleanVar(value=self.check_startup_status())

        self._build_grid()

    def _build_grid(self):
        padding = {"padx": 10, "pady": 10}

        tk.Label(self, text="Delimiter String:").grid(
            row=0, column=0, sticky="e", **padding
        )
        tk.Entry(self, textvariable=self.delimiter_var, width=50).grid(
            row=0, column=1, **padding
        )

        tk.Label(self, text="Copy Hotkey:").grid(row=1, column=0, sticky="e", **padding)
        tk.Entry(self, textvariable=self.hotkey_var, width=50).grid(
            row=1, column=1, **padding
        )

        tk.Label(self, text="WebUI Directory:").grid(
            row=2, column=0, sticky="e", **padding
        )
        tk.Entry(self, textvariable=self.webui_var, width=50).grid(
            row=2, column=1, **padding
        )

        self.toggle_btn = tk.Button(
            self,
            text="Start Service",
            command=self.toggle_service,
            width=20,
            bg="#4CAF50",
            fg="white",
        )
        self.toggle_btn.grid(row=3, column=0, columnspan=2, pady=20)
        
        tk.Checkbutton(
            self,
            text="Run on Windows Startup",
            variable=self.startup_var,
            command=self.toggle_startup_registry
        ).grid(row=3, column=0, columnspan=2, pady=(10, 0))

        # Push the Start button down one row
        self.toggle_btn = tk.Button(self, text="Start Service", command=self.toggle_service, width=20, bg="#4CAF50", fg="white")
        self.toggle_btn.grid(row=4, column=0, columnspan=2, pady=20)


    def check_startup_status(self) -> bool:
        """Checks if the app is currently set to run on startup."""
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ)
            winreg.QueryValueEx(key, "WC3BattleTagCopier")
            winreg.CloseKey(key)
            return True
        except FileNotFoundError:
            return False
        except Exception as e:
            logger.error(f"Error checking startup registry: {e}")
            return False

    def toggle_startup_registry(self):
        """Adds or removes the executable from the Windows Startup registry."""
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        app_name = "WC3BattleTagCopier"

        # Determine the path of the executable
        if getattr(sys, 'frozen', False):
            # Running as a PyInstaller compiled executable
            exe_path = sys.executable
        else:
            # Running as a raw python script
            exe_path = os.path.abspath(sys.argv[0])

        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS)
            if self.startup_var.get():
                # Add to startup (wrap path in quotes to handle spaces)
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, f'"{exe_path}"')
                logger.info("Added to Windows startup.")
            else:
                # Remove from startup
                try:
                    winreg.DeleteValue(key, app_name)
                    logger.info("Removed from Windows startup.")
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
        except Exception as e:
            messagebox.showerror("Registry Error", f"Failed to modify startup settings: {e}")
            # Revert checkbox state on failure
            self.startup_var.set(not self.startup_var.get())


    def resource_path(self, relative_path):
        """Get absolute path to resource, works for dev and for PyInstaller"""
        try:
            base_path = sys._MEIPASS
        except AttributeError:
            base_path = os.path.abspath(".")
        return os.path.join(base_path, relative_path)

    def toggle_service(self):
        if self.is_running:
            self.stop_service()
        else:
            self.start_service()

    def start_service(self):
        webui_dir = self.webui_var.get()
        os.makedirs(webui_dir, exist_ok=True)

        # 1. Flip the registry flag just like setup.ts
        if not enable_webui_in_registry(True):
            messagebox.showwarning(
                "Registry Warning",
                "Could not set 'Allow Local Files' registry key. The game might not load the WebUI.",
            )

        # 2. Copy the webhook HTML and JS payload files
        files_to_copy = ["index.html", "index.js"]
        for file_name in files_to_copy:
            local_file = self.resource_path(file_name)
            target_file = os.path.join(webui_dir, file_name)

            if os.path.exists(local_file):
                try:
                    shutil.copyfile(local_file, target_file)
                    logger.info(f"Copied {local_file} to {target_file}")
                except PermissionError:
                    messagebox.showerror(
                        "Permission Error",
                        f"Cannot write to {webui_dir}.\nPlease run as Administrator.",
                    )
                    return
            else:
                logger.warning(
                    f"Local '{local_file}' not found. Ensure both index.html and index.js exist."
                )

        self.is_running = True
        self.toggle_btn.config(text="Stop Service", bg="#f44336")

        self.service_thread = threading.Thread(
            target=self.run_asyncio_loop, daemon=True
        )
        self.service_thread.start()

    def stop_service(self):
        if self.loop and self.loop.is_running() and self.shutdown_event:
            self.loop.call_soon_threadsafe(self.shutdown_event.set)

        self.is_running = False
        self.toggle_btn.config(text="Start Service", bg="#4CAF50")

    def run_asyncio_loop(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        delimiter = self.delimiter_var.get()
        hotkey = self.hotkey_var.get()
        self.shutdown_event = asyncio.Event()

        # Spin up the Relay Server inside this process
        relay_server = GameClientServer(host="127.0.0.1", port=8888)

        async def run_all():
            server_task = self.loop.create_task(relay_server.start_server())
            queue_task = self.loop.create_task(relay_server.process_message_queue())

            # Start UI websocket hook and wait for the stop button
            await start_async_service(hotkey, delimiter, self.shutdown_event)

            server_task.cancel()
            queue_task.cancel()

        try:
            self.loop.run_until_complete(run_all())
        finally:
            self.loop.close()
            logger.info("Asyncio loop closed.")


if __name__ == "__main__":
    app = AppUI()
    app.mainloop()
