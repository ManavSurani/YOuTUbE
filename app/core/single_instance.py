"""Single-instance application guard using Qt local socket IPC.

Guarantees only one instance of YOuTUbE runs simultaneously.
When a secondary instance is launched:
1. It sends an activation signal (plus any CLI arguments) to the running primary instance.
2. The primary instance brings its window to the foreground and un-minimizes.
3. The secondary instance immediately terminates with exit code 0.
"""

from typing import Callable, Optional
from PySide6.QtCore import QObject, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from app.version import APP_NAME
from app.core.logger import get_logger

SERVER_NAME = f"{APP_NAME}_SingleInstance_IPC_Server"


class SingleInstance(QObject):
    """Manages single-instance detection and window activation IPC."""

    message_received = Signal(str)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._server: Optional[QLocalServer] = None

    @staticmethod
    def is_another_instance_running(message: str = "") -> bool:
        """Probe if another instance is already running.

        If running, sends message and returns True.
        """
        socket = QLocalSocket()
        socket.connectToServer(SERVER_NAME)
        if socket.waitForConnected(1000):
            payload = (message.strip() or "ACTIVATE") + "\n"
            socket.write(payload.encode("utf-8"))
            socket.flush()
            socket.waitForBytesWritten(1000)
            socket.waitForDisconnected(500)
            socket.close()
            get_logger().info("Secondary instance detected; signalled primary instance to activate.")
            return True
        return False

    def start_server(self, on_message: Optional[Callable[[str], None]] = None) -> bool:
        """Start listening for activation requests from secondary instances."""
        if on_message:
            self.message_received.connect(on_message)

        # Clean up any stale pipe/socket from a previous crash
        QLocalServer.removeServer(SERVER_NAME)

        self._server = QLocalServer(self)
        self._server.newConnection.connect(self._handle_new_connection)
        success = self._server.listen(SERVER_NAME)
        if success:
            get_logger().info(f"SingleInstance server listening on '{SERVER_NAME}'.")
        else:
            get_logger().warning(f"SingleInstance failed to listen: {self._server.errorString()}")
        return success

    def _handle_new_connection(self) -> None:
        if not self._server:
            return
        socket = self._server.nextPendingConnection()
        if not socket:
            return

        read_done = [False]

        def read_data():
            if read_done[0]:
                return
            try:
                raw = socket.readAll().data()
                if raw:
                    read_done[0] = True
                    text = raw.decode("utf-8", errors="replace").strip()
                    if text:
                        self.message_received.emit(text)
                    socket.disconnectFromServer()
            except Exception as exc:
                get_logger().debug(f"Error reading socket data: {exc}")

        socket.readyRead.connect(read_data)
        socket.disconnected.connect(socket.deleteLater)
        if socket.bytesAvailable() > 0:
            read_data()
