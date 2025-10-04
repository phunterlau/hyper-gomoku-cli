"""Controller responsible for interpreting user commands."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict

from .game import Game


class Command:
    MOVE_UP = "up"
    MOVE_DOWN = "down"
    MOVE_LEFT = "left"
    MOVE_RIGHT = "right"
    PLACE = "place"
    RESET = "reset"
    SKILL_PREFIX = "skill:"
    SECRET_REPORT = "secret-report"


@dataclass
class Controller:
    """Translate symbolic commands into game actions."""

    game: Game

    def __post_init__(self) -> None:
        self._handlers: Dict[str, Callable[[], None]] = {
            Command.MOVE_UP: lambda: self.game.move_cursor(-1, 0),
            Command.MOVE_DOWN: lambda: self.game.move_cursor(1, 0),
            Command.MOVE_LEFT: lambda: self.game.move_cursor(0, -1),
            Command.MOVE_RIGHT: lambda: self.game.move_cursor(0, 1),
            Command.PLACE: self.game.place_at_cursor,
            Command.RESET: self.game.reset,
            Command.SECRET_REPORT: self.game.report_to_referee,
        }
        for skill_name in self.game.skill_registry:
            self._handlers[f"{Command.SKILL_PREFIX}{skill_name}"] = (
                lambda name=skill_name: self.game.use_skill(name)
            )

    def handle_input(self, command: str) -> None:
        if self.game.is_finished and command != Command.RESET:
            return

        handler = self._handlers.get(command)
        if handler is None:
            raise ValueError(f"未知指令：{command}")
        handler()
