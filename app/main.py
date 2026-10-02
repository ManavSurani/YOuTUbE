import sys
from PySide6.QtWidgets import QApplication
from app.version import APP_NAME
from app.core.settings import load_settings
from app.ui.theme import build_qss
from app.ui.splash import SplashScreen
from app.ui.main_window import MainWindow
from app.core.paths import purge_stale_tmp


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)

    # Clean up stale tmp files from previous sessions (Phase 1 / B4)
    purge_stale_tmp()

    settings = load_settings()
    theme = settings.get("theme", "dark")
    app.setStyleSheet(build_qss(theme))

    main_window_holder = []

    def on_startup_completed():
        win = MainWindow()
        main_window_holder.append(win)
        win.show()

    splash = SplashScreen()
    splash.startup_completed.connect(on_startup_completed)
    splash.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
