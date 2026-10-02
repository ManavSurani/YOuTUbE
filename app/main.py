import sys
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from app.version import APP_NAME
from app.core.settings import load_settings
from app.ui.theme import build_qss
from app.ui.splash import SplashScreen
from app.ui.main_window import MainWindow
from app.core.paths import purge_stale_tmp
from app.core.single_instance import SingleInstance


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
        if main_window_holder:
            win = main_window_holder[0]
            win.setWindowState((win.windowState() & ~Qt.WindowState.WindowMinimized) | Qt.WindowState.WindowActive)
            win.show()
            win.raise_()
            win.activateWindow()
            if msg and msg != "ACTIVATE" and "youtu" in msg.lower():
                win.video_tab.url_input.setText(msg.strip())
        elif splash_holder and splash_holder[0].isVisible():
            splash_holder[0].raise_()
            splash_holder[0].activateWindow()

    single_instance.start_server(on_secondary_instance_message)

    def on_startup_completed():
        from app.core.history_service import repair_existing_rows
        repair_existing_rows()
        win = MainWindow()
        main_window_holder.append(win)
        win.show()

    splash = SplashScreen()
    splash_holder.append(splash)
    splash.startup_completed.connect(on_startup_completed)
    splash.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
