"""Overlay dialog rendering utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List

from .text_utils import display_width, pad_to_width, truncate_to_width

RESET = "\033[0m"
BOLD = "\033[1m"
FG_WHITE = "\033[37m"
FG_MAGENTA = "\033[35m"
FG_CYAN = "\033[36m"


@dataclass
class DialogOverlay:
    """Represents a blocking overlay dialog rendered above the board."""

    width: int = 40

    def render(self, lines: Iterable[str], screen_width: int, screen_height: int) -> List[str]:
        content = self._wrap_lines(lines)
        max_display = max((display_width(line) for line in content), default=0)
        box_width = max(4, min(self.width, max_display + 4))
        inner_width = max(box_width - 4, 0)

        framed: List[tuple[str, bool]] = []
        framed.append((("┌" + "─" * (box_width - 2) + "┐"), True))
        for line in content:
            truncated = truncate_to_width(line, inner_width)
            padded = pad_to_width(truncated, inner_width)
            framed.append((f"│ {padded} │", False))
        framed.append((("└" + "─" * (box_width - 2) + "┘"), True))

        top_padding = max((screen_height - len(framed)) // 2, 0)
        side_padding = max((screen_width - box_width) // 2, 0)

        padded_lines: List[str] = [" " * screen_width for _ in range(top_padding)]
        for line, is_border in framed:
            with_margin = " " * side_padding + line
            trimmed = truncate_to_width(with_margin, screen_width)
            padded = pad_to_width(trimmed, screen_width)
            padded_lines.append(self._color_line(padded, border=is_border))
        while len(padded_lines) < screen_height:
            padded_lines.append(" " * screen_width)
        return padded_lines[:screen_height]

    def _wrap_lines(self, lines: Iterable[str]) -> List[str]:
        processed: List[str] = []
        for line in lines:
            processed.append(str(line).strip())
        if not processed:
            processed = ["(无消息)"]
        return processed

    def _color_line(self, text: str, *, border: bool = False) -> str:
        if border:
            return f"{FG_MAGENTA}{BOLD}{text}{RESET}"
        return f"{FG_CYAN}{BOLD}{text}{RESET}"
