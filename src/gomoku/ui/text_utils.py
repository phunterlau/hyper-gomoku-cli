"""Utility helpers for measuring and shaping terminal text width."""

from __future__ import annotations

import re
import unicodedata

__all__ = ["display_width", "truncate_to_width", "pad_to_width", "strip_ansi"]

ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")


def strip_ansi(text: str) -> str:
    return ANSI_ESCAPE_RE.sub("", text)


def _char_width(ch: str) -> int:
    if unicodedata.combining(ch):
        return 0
    east_asian = unicodedata.east_asian_width(ch)
    if east_asian in ("F", "W"):
        return 2
    return 1


def display_width(text: str) -> int:
    return sum(_char_width(ch) for ch in strip_ansi(text))


def truncate_to_width(text: str, max_width: int) -> str:
    if max_width <= 0:
        return ""
    result_chars: list[str] = []
    width = 0
    for ch in text:
        ch_width = _char_width(ch)
        if width + ch_width > max_width:
            break
        result_chars.append(ch)
        width += ch_width
    return "".join(result_chars)


def pad_to_width(text: str, width: int, pad_char: str = " ") -> str:
    current = display_width(text)
    if current >= width:
        return text
    pad_needed = width - current
    return text + pad_char * pad_needed
