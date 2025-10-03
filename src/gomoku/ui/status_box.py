"""Status box rendering helpers for the terminal UI."""

from __future__ import annotations

from typing import Iterable, List

from .text_utils import pad_to_width, truncate_to_width


class StatusBox:
    """Render a fixed-height ASCII bordered status panel."""

    def __init__(self, height: int = 3, min_width: int = 20) -> None:
        if height < 1:
            raise ValueError("Status box height must be positive")
        self.height = height
        self.min_width = min_width

    def render(self, lines: Iterable[str], width: int) -> List[str]:
        inner_width = max(self.min_width, width)
        sanitized = self._prepare_lines(lines, inner_width)
        top = "┌" + "─" * inner_width + "┐"
        bottom = "└" + "─" * inner_width + "┘"
        body = [f"│{line}│" for line in sanitized]
        return [top, *body, bottom]

    def _prepare_lines(self, lines: Iterable[str], inner_width: int) -> List[str]:
        collected: List[str] = []
        for line in lines:
            text = str(line or "")
            trimmed = truncate_to_width(text, inner_width)
            collected.append(pad_to_width(trimmed, inner_width))
            if len(collected) == self.height:
                break
        while len(collected) < self.height:
            collected.append(pad_to_width("", inner_width))
        return collected
