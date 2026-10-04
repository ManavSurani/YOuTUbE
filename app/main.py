import sys
from typing import Optional
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import QApplication
from app.version import APP_NAME, APP_VERSION
from app.core.settings import load_settings, save_settings
from app.ui.theme import build_qss
from app.ui.splash import SplashScreen
from app.ui.main_window import MainWindow
from app.core.paths import purge_stale_tmp, DEFAULT_DOWNLOADS
from app.core.single_instance import SingleInstance


class HistoryRepairWorker(QThread):
    repaired = Signal(int)

    def __init__(self, download_dir: str, parent=None) -> None:
        super().__init__(parent)
        self.download_dir = download_dir

    def run(self) -> None:
        from app.core.history_service import repair_existing_rows
        from app.core.logger import get_logger
        count = repair_existing_rows(download_dir=self.download_dir)
        get_logger().info(f"History repair completed: {count} rows repaired.")
        self.repaired.emit(count)


def maybe_start_history_repair(win: MainWindow, settings: Optional[dict] = None) -> Optional[HistoryRepairWorker]:
    if settings is None:
        settings = load_settings()
    last_repair_ver = settings.get("history_repair_version", "")
    if last_repair_ver == APP_VERSION:
        return None

    download_dir = settings.get("download_dir", str(DEFAULT_DOWNLOADS))
    worker = HistoryRepairWorker(download_dir=download_dir, parent=win)

    def on_repaired(count: int) -> None:
        if count > 0:
            win.history_tab.refresh_items()
        curr_settings = load_settings()
        curr_settings["history_repair_version"] = APP_VERSION
        save_settings(curr_settings)

    worker.repaired.connect(on_repaired)
    win._history_repair_worker = worker
    worker.start()
    return worker


def handle_secondary_instance_message(msg: str, main_window_holder: list, splash_holder: list) -> None:
    """Handle message from secondary instance: bring window forward and insert valid YouTube links."""
    from app.core.url_tools import is_youtube_url
    if main_window_holder:
        win = main_window_holder[0]
        win.setWindowState((win.windowState() & ~Qt.WindowState.WindowMinimized) | Qt.WindowState.WindowActive)
        win.show()
        win.raise_()
        win.activateWindow()
        clean_msg = msg.strip()
        if clean_msg.startswith("ACTIVATE "):
            clean_msg = clean_msg[len("ACTIVATE "):].strip()
        if clean_msg and clean_msg != "ACTIVATE" and is_youtube_url(clean_msg):
            win.video_tab.url_input.setText(clean_msg)
    elif splash_holder and splash_holder[0].isVisible():
        splash_holder[0].raise_()
        splash_holder[0].activateWindow()


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)

    # Single-instance guard check (Chunk 8.2 Task 5)
    cli_arg = sys.argv[1] if len(sys.argv) > 1 else ""
    if SingleInstance.is_another_instance_running(cli_arg):
        return 0

    single_instance = SingleInstance()

    # Clean up stale tmp files from previous sessions (Phase 1 / B4)
    purge_stale_tmp()

    settings = load_settings()
    theme = settings.get("theme", "dark")
    app.setStyleSheet(build_qss(theme))

    main_window_holder = []
    splash_holder = []

    def on_secondary_instance_message(msg: str):
        handle_secondary_instance_message(msg, main_window_holder, splash_holder)

    single_instance.start_server(on_secondary_instance_message)

    def on_startup_completed():
        win = MainWindow()
        main_window_holder.append(win)
        win.show()
        maybe_start_history_repair(win, settings=settings)

    splash = SplashScreen()
    splash_holder.append(splash)
    splash.startup_completed.connect(on_startup_completed)
    splash.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
