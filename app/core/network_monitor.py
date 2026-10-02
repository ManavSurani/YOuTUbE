"""Network connectivity monitor watcher thread."""

import socket
import time
from typing import Callable, Optional
from PySide6.QtCore import QThread, Signal
from app.core.logger import get_logger


def default_connectivity_check(timeout: float = 3.0) -> bool:
    """Check connectivity to youtube.com:443 with fallback to 1.1.1.1:53."""
    hosts = [("youtube.com", 443), ("1.1.1.1", 53)]
    for host, port in hosts:
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except Exception:
            continue
    return False


class NetworkMonitor(QThread):
    """Background thread checking internet reachability every 4s with 2-failure debouncing."""

    went_offline = Signal()
    came_online = Signal()
    state_changed = Signal(bool)  # True = online, False = offline

    def __init__(
        self,
        check_fn: Optional[Callable[[], bool]] = None,
        check_interval: float = 4.0,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.check_fn = check_fn or default_connectivity_check
        self.check_interval = check_interval
        self._running = True
        self._is_online = True
        self._consecutive_failures = 0

    def is_online(self) -> bool:
        return self._is_online

    def stop(self) -> None:
        """Signal the watcher thread to stop cleanly."""
        self._running = False

    def run(self) -> None:
        logger = get_logger()
        logger.info("Network monitor started.")

        while self._running:
            success = self.check_fn()

            if success:
                self._consecutive_failures = 0
                if not self._is_online:
                    self._is_online = True
                    logger.info("Internet connection restored.")
                    self.came_online.emit()
                    self.state_changed.emit(True)
            else:
                self._consecutive_failures += 1
                if self._consecutive_failures >= 2 and self._is_online:
                    self._is_online = False
                    logger.warning("Internet connection lost.")
                    self.went_offline.emit()
                    self.state_changed.emit(False)

            # Sleep in small increments for prompt thread termination
            elapsed = 0.0
            step = min(0.01, self.check_interval)
            while self._running and elapsed < self.check_interval:
                time.sleep(step)
                elapsed += step

        logger.info("Network monitor stopped.")
