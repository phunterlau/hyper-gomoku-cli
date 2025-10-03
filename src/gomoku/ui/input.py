"""Keyboard input abstractions for the terminal UI."""

from __future__ import annotations

try:  # pragma: no cover - optional dependency
    import readchar
except ModuleNotFoundError:  # pragma: no cover - fallback
    readchar = None  # type: ignore


def get_key() -> str:
    """Return the next key pressed by the player.

    Falls back to raising :class:`NotImplementedError` when ``readchar`` is not
    available so that non-interactive tests can run without the dependency.
    """

    if readchar is None:
        raise NotImplementedError("readchar is not installed; keyboard input unavailable")
    char = readchar.readkey()
    return char
