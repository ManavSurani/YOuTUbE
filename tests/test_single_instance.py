"""Unit tests for SingleInstance application guard."""

import time
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from app.core.single_instance import SingleInstance, SERVER_NAME


def test_single_instance_detection():
    app = QApplication.instance() or QApplication(sys.argv)
    # Ensure any lingering test server is purged
    QLocalServer.removeServer(SERVER_NAME)

    # 1. When no server is running, returns False
    assert not SingleInstance.is_another_instance_running("hello")

    # 2. Start server
    instance = SingleInstance()
    received_messages = []
    success = instance.start_server(lambda msg: received_messages.append(msg))
    assert success is True

    # 3. Simulate secondary instance connecting and sending activation command
    client_socket = QLocalSocket()
    client_socket.connectToServer(SERVER_NAME)
    assert client_socket.waitForConnected(1000)
    client_socket.write(b"ACTIVATE https://youtube.com/watch?v=123\n")
    client_socket.flush()
    client_socket.waitForBytesWritten(1000)

    # Process Qt events to allow server to receive and parse message
    for _ in range(25):
        app.processEvents()
        if received_messages:
            break
        time.sleep(0.02)

    client_socket.waitForDisconnected(500)
    client_socket.close()

    assert len(received_messages) == 1
    assert "https://youtube.com/watch?v=123" in received_messages[0]

    # 4. Clean up
    if instance._server:
        instance._server.close()
    QLocalServer.removeServer(SERVER_NAME)
    for _ in range(5):
        app.processEvents()


def test_secondary_instance_message_ignores_junk_and_accepts_valid_url():
    """Chunk 9.3 (E12): valid YouTube link fills link box; 'hello' does not."""
    from unittest.mock import MagicMock
    from PySide6.QtCore import Qt
    from app.main import handle_secondary_instance_message

    mock_win = MagicMock()
    mock_win.windowState.return_value = Qt.WindowState.WindowNoState

    # 1. Send "hello" -> window activated, but setText NOT called with "hello"
    handle_secondary_instance_message("hello", [mock_win], [])
    mock_win.show.assert_called()
    mock_win.video_tab.url_input.setText.assert_not_called()

    # 2. Send "ACTIVATE hello" -> setText NOT called
    handle_secondary_instance_message("ACTIVATE hello", [mock_win], [])
    mock_win.video_tab.url_input.setText.assert_not_called()

    # 3. Send valid YouTube link -> setText called with the link
    valid_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    handle_secondary_instance_message(valid_url, [mock_win], [])
    mock_win.video_tab.url_input.setText.assert_called_once_with(valid_url)

    # 4. Send "ACTIVATE https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    mock_win.video_tab.url_input.setText.reset_mock()
    handle_secondary_instance_message(f"ACTIVATE {valid_url}", [mock_win], [])
    mock_win.video_tab.url_input.setText.assert_called_once_with(valid_url)

