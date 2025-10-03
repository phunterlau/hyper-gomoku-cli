"""Overlay manager for blocking dialogs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List, Optional

from .dialog import DialogOverlay


@dataclass
class OverlayManager:
    """Manage a queue of overlay dialogs to display over the TUI."""

    overlay: DialogOverlay = field(default_factory=DialogOverlay)
    active_lines: Optional[List[str]] = None

    def show(self, lines: Iterable[str]) -> None:
        self.active_lines = [str(line) for line in lines]

    def clear(self) -> None:
        self.active_lines = None

    def render(self, screen_width: int, screen_height: int) -> List[str]:
        if self.active_lines is None:
            return []
        return self.overlay.render(self.active_lines, screen_width, screen_height)

    def is_active(self) -> bool:
        return self.active_lines is not None