"""UI kit package providing design-system compliant widgets."""

from app.ui.kit.anim import create_animation, is_animations_enabled
from app.ui.kit.buttons import AnimatedButton, IconButton
from app.ui.kit.checkbox import AnimatedCheckBox
from app.ui.kit.inline_message import InlineMessage
from app.ui.kit.progress_card import ProgressCard
from app.ui.kit.thumb_label import ThumbLabel
from app.ui.kit.toast import Toast

__all__ = [
    "create_animation",
    "is_animations_enabled",
    "AnimatedButton",
    "IconButton",
    "AnimatedCheckBox",
    "InlineMessage",
    "ProgressCard",
    "ThumbLabel",
    "Toast",
]
