# socket_comm/game_socket.py
import asyncio
import json
import time
from pydantic import BaseModel, ValidationError
from payloads.receive_payloads import RecMessage
from payloads.send_payloads import SendMessage
import websockets


import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class MessageQueue:
    def __init__(self):
        self.queue = asyncio.Queue()

    async def put(self, message):
        await self.queue.put(message)

    async def get(self):
        return await self.queue.get()

    async def empty(self):
        return self.queue.empty()


class SendToGame(BaseModel):
    """SendToGame

    A Pydantic model representing a message sent to the game server.

    Attributes
    ----------
    messageType : str
        The type of the message, fixed to 'sendToGame'.
    battletag : str | None
        The battletag of the game connection to send the message to.
    username : str | None
        The username of the game connection to send the message to.
    data : SendMessage
        The payload containing the message to be sent.
    """
    messageType: str = "sendToGame"
    battletag: str | None = None
    username: str | None = None
    data: SendMessage

# a class to handle sending messages between the game client(s) and application clients
class GameClientServer:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.current_game_task: asyncio.Task | None = None
        self.connected_app_clients = set()  # Will store WebSocket objects
        self.app_client_addresses = {}  # Map from WebSocket object to address
        self.rec_message_queue = MessageQueue()
        self.send_message_queue = MessageQueue()

        self.spammy_messages = {"OnChannelUpdate", "GameList", "GameListUpdate", "Options", "OptionsData"}

    async def ws_handler(self, websocket):
        """Handles incoming messages on the WebSocket server."""
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    # Case 1: Game UI registration
                    if data.get("messageType") == "clientWebSocket":
                        game_websocket_address = data["data"]
                        print(f"Received game webui address: {game_websocket_address}")
                        if self.current_game_task and not self.current_game_task.done():
                            print("Cancelling old game connection...")
                            self.current_game_task.cancel()
                            try:
                                await self.current_game_task
                            except asyncio.CancelledError:
                                pass
                        self.current_game_task = asyncio.create_task(
                            self.establish_connection_to_game(game_websocket_address, 31.0)
                        )
                    # Case 2: App client registration
                    elif data.get("messageType") == "appClient":
                        print(f"App client connected: {websocket}")
                        self.connected_app_clients.add(websocket)
                        # Store the address for later use
                        self.app_client_addresses[websocket] = str(websocket.remote_address) if hasattr(websocket, 'remote_address') else "unknown"
                    # Case 3: App client wants to send payloads to the game
                    elif data.get("messageType") == "sendToGame":
                        try:
                            print(f"Message received {data["data"]}")
                            validated_request = SendToGame.model_validate(data)
                            await self.send_message_queue.put(validated_request.data)
                        except ValidationError as e:
                            print(f"Validation failed for incoming payload: {e}")
                except json.JSONDecodeError:
                    print("Invalid JSON received")
        finally:
            # Guaranteed cleanup when the loop breaks or connection drops
            if websocket in self.connected_app_clients:
                self.connected_app_clients.remove(websocket)
                print(f"App client disconnected: {websocket.remote_address}")


    async def establish_connection_to_game(self, address: str, timeout: float | None = None):
        try:
            while True:
                start_time = time.monotonic()  # reset each time after success

                while True:
                    # If timeout is set and exceeded before connection success, stop retrying
                    if timeout is not None and (time.monotonic() - start_time) >= timeout:
                        print(f"Connection attempt timed out after {timeout} seconds without success.")
                        return

                    try:
                        # Only timeout applies to connection phase
                        async with websockets.connect(address) as ws:
                            print(f"Connected to client {address}")

                            # Reset timeout timer after a successful connection
                            start_time = time.monotonic()

                            # Run receive and send concurrently until disconnection
                            await asyncio.gather(
                                self._rec_payloads(ws),
                                self._send_payloads(ws)
                            )

                    except (OSError, websockets.WebSocketException, ConnectionRefusedError) as e:
                        print(f"Failed to connect to {address}: {e}. Retrying in 10 seconds...")
                        await asyncio.sleep(10)
        except asyncio.CancelledError:
            print(f"Connection task for {address} cancelled.")
            raise  # re-raise so task truly ends


    async def _rec_payloads(self, ws):
        """Receives messages from the client and puts them into the receive queue."""
        async for message in ws:
            data = json.loads(message)
            try:
                # Validates that the game sent a recognized messageType and payload structure
                validated_msg = RecMessage.model_validate(data)
                # You can now safely pass the raw message string OR the validated model
                await self.rec_message_queue.put(message)
            except ValidationError as e:
                print(f"Unrecognized or malformed game message: {e}")
            # optional logging
            if data.get("messageType") in self.spammy_messages:
                logger.debug(f"Received from game: {message}")
            else:
                logger.info(f"Received from game: {message}")


    async def _send_payloads(self, ws):
        """Sends messages from the send queue to the client."""
        while True:
            payload = await self.send_message_queue.get()
            try:
                if not isinstance(payload, str):
                    payload_str = json.dumps(payload)
                await ws.send(payload_str)
                print(f"Sent to game: {payload_str}")
            except websockets.exceptions.ConnectionClosed as e:
                print(f"WebSocket connection closed in _send_payloads: {e}")
                await self.send_message_queue.put(payload)
                raise  # Re-raise to allow cancellation of other tasks
            except websockets.WebSocketException as e:
                print(f"Failed to send to game: {e}")
                await self.send_message_queue.put(payload)


    async def _send_payload_to_game(self, payload):
        """Queue a payload to be sent to the client WebSocket."""
        print("queueing payload to send to game")
        await self.send_message_queue.put(payload)


    async def _get_payload_from_game(self) -> str:
        message = await self.rec_message_queue.get()
        return message


    async def send_to_app_clients(self, message: str):
        """Forwards the message to all connected WebSocket addresses."""
        # print(f"Sending message to {len(self.connected_app_clients)} clients: {message}")

        # Create a copy of the set to avoid modification during iteration
        clients_copy = set(self.connected_app_clients)

        for client in clients_copy:
            try:
                # Send directly to the WebSocket object, not connect to it
                await client.send(message)
                # print(f"Message forwarded to client: {message}")
            except (websockets.WebSocketException, ConnectionError) as e:
                print(f"Failed to send to client: {e}. Removing from connected clients.")
                # Remove failed client from the list
                try:
                    self.connected_app_clients.remove(client)
                    self.app_client_addresses.pop(client, None)
                except KeyError:
                    pass  # Client was already removed


    async def process_message_queue(self):
        """Processes messages from rec_message_queue and forwards them to the forward server."""
        while True:
            message = await self.rec_message_queue.get()
            # print(f"Forwarding message: {message}")
            await self.send_to_app_clients(message)


    async def start_server(self):
        """Starts the WebSocket server."""
        stop = asyncio.Event()

        # Optional: Add signal handlers here to set stop.set() on Ctrl+C

        async with websockets.serve(self.ws_handler, self.host, self.port) as server:
            print(f"Server started on {self.host}:{self.port}")
            await stop.wait() # Waits until the event is set instead of forever

        print("Server shutting down cleanly.")


async def main():
    server = GameClientServer(host="127.0.0.1", port=8888)
    await asyncio.gather(
        server.start_server(),
        server.process_message_queue()
    )

if __name__ == "__main__":
    asyncio.run(main())

# Received from game: {"messageType":"GameVersion","payload":{"gameVersion":"2.0.3.23101 x86_64"}}
# Received from game: {"messageType":"BuildType","payload":{"buildType":"retail"}}
# Received from game: {"messageType":"UpdateUserInfo","payload":{"user":{"username":"Numba1stunna#1124","localPlayerName":"","battleTag":"Numba1stunna#1124","avatarId":"","isSelf":true,"shouldDisableCustomGames":false,"isAuthenticated":false,"isTeamMember":false,"isTeamLeader":false,"isInGame":false,"ageRatingRequired":"","userRegion":"","regionBlockedContent":false,"gatewayId":0,"seasonalInfoSeen":true,"isHDModeEnabled":false,"hasRequiredHDHardware":true,"hasReforged":false,"isOfflineAllowed":true}}}
# Received from game: {"messageType":"SetMainMenuTheme","payload":{"mainMenuTheme":2.0}}
