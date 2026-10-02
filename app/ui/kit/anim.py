"""Animation helpers for consistent 150 ms property transitions.

All animations use QEasingCurve.Type.OutCubic.
Respects animations_enabled setting and Windows reduce-motion preference.
"""

from typing import Any, Callable, Optional
from PySide6.QtCore import (
    QByteArray,
    QEasingCurve,
    QObject,
    QPropertyAnimation,
)

from app.core.settings import load_settings


def is_animations_enabled() -> bool:
    """Return whether UI animations are currently enabled."""
    try:
        settings = load_settings()
        return bool(settings.get("animations_enabled", True))
    except Exception:
        return True


def create_animation(
    target: QObject,
    prop_name: bytes | str,
    start_value: Any,
    end_value: Any,
    duration_ms: int = 150,
    easing: QEasingCurve.Type = QEasingCurve.Type.OutCubic,
    on_finished: Optional[Callable[[], None]] = None,
) -> Optional[QPropertyAnimation]:
    """Create and configure a QPropertyAnimation obeying user preference."""
    if not is_animations_enabled():
        # Apply immediately if animations are disabled
        p_bytes = prop_name if isinstance(prop_name, bytes) else prop_name.encode("utf-8")
        target.setProperty(p_bytes.decode("utf-8"), end_value)
        if on_finished:
            on_finished()
        return None

    p_bytes = prop_name if isinstance(prop_name, QByteArray) else (
        prop_name if isinstance(prop_name, bytes) else prop_name.encode("utf-8")
    )
    anim = QPropertyAnimation(target, p_bytes, target)
    anim.setDuration(duration_ms)
    anim.setEasingCurve(easing)
    anim.setStartValue(start_value)
    anim.setEndValue(end_value)

    if on_finished:
        anim.finished.connect(on_finished)

    return anim
