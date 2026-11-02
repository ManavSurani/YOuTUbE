"""Animation helpers and the app's motion tokens.

Every UI animation uses one of these durations (OutCubic unless noted) and is skipped
when 'Reduce motion' is on (settings: animations_enabled = False).
"""

from typing import Any, Callable, Optional
from PySide6.QtCore import (
    QByteArray,
    QPoint,
    QEasingCurve,
    QObject,
    QPropertyAnimation,
)

from app.core.settings import load_settings

FAST = 120        # hover, press, focus, small fades
BASE = 180        # show/hide, tab underline, value changes, error shake
SLOW = 260        # height expand/collapse
CELEBRATE = 300   # the one "done" pulse (OutBack)
SHIMMER_MS = 1600  # ambient loop on the active progress bar (only while bytes move)


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
    duration_ms: int = BASE,
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


def shake(widget: QObject) -> Optional[QPropertyAnimation]:
    """Small horizontal shake (3 x 4 px) for invalid input; None when motion is reduced."""
    if not is_animations_enabled():
        return None
    start = widget.pos()
    anim = QPropertyAnimation(widget, b"pos", widget)
    anim.setDuration(BASE)
    for step, dx in ((0.0, 0), (0.17, -4), (0.33, 4), (0.5, -4), (0.67, 4), (0.83, -2), (1.0, 0)):
        anim.setKeyValueAt(step, start + QPoint(dx, 0))
    anim.start(QPropertyAnimation.DeletionPolicy.KeepWhenStopped)
    return anim
