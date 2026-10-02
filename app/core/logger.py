import logging
from logging.handlers import RotatingFileHandler
from app.core.paths import LOG_FILE, ensure_dirs

_logger: logging.Logger | None = None


def setup_logger() -> logging.Logger:
    """Initialize rotating file logger. No console output is ever attached."""
    global _logger
    if _logger is not None:
        return _logger

    ensure_dirs()
    logger = logging.getLogger("youtube_app")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if not logger.handlers:
        handler = RotatingFileHandler(
            str(LOG_FILE),
            maxBytes=1_000_000,
            backupCount=2,
            encoding="utf-8",
        )
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    _logger = logger
    return _logger


def get_logger() -> logging.Logger:
    """Get the application logger."""
    if _logger is None:
        return setup_logger()
    return _logger
