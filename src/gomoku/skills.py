"""Skill definitions for the Gomoku game."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, List, Tuple

if TYPE_CHECKING:  # pragma: no cover - circular import guard
    from .game import Game, Player

Coordinate = Tuple[int, int]


@dataclass(frozen=True)
class SkillResult:
    """Outcome metadata describing a skill activation."""

    skill_name: str
    player_name: str
    description: str
    details: Dict[str, object]


@dataclass(frozen=True)
class Skill:
    """Base configuration for a skill."""

    name: str
    description: str
    cooldown_turns: int
    initial_cooldown: int = 0

    def apply(self, game: "Game", player: "Player", rng: random.Random) -> SkillResult:
        raise NotImplementedError


class StoneStormSkill(Skill):
    """飞沙走石 — Remove a random opponent stone."""

    def __init__(self) -> None:
        super().__init__(
            name="飞沙走石",
            description="随机移除对方棋子的一枚。",
            cooldown_turns=5,
            initial_cooldown=5,
        )

    def apply(self, game: "Game", player: "Player", rng: random.Random) -> SkillResult:
        opponent_coords = list(game.occupied_by_player(player.opponent))
        if not opponent_coords:
            raise ValueError("对方棋盘上没有可移除的棋子")

        cursor_target = None
        if game.board.get(game.cursor) == player.opponent.stone:
            cursor_target = game.cursor

        target = cursor_target or rng.choice(opponent_coords)
        removed_stone = game.board.remove_stone(target)
        if game.last_move and game.last_move.coordinate == target:
            game.last_move = None

        if cursor_target:
            game.set_cursor(target)

        return SkillResult(
            skill_name=self.name,
            player_name=player.name,
            description=f"移除了对手在 {target} 的棋子",
            details={"removed": target, "stone": removed_stone},
        )


class StillWatersSkill(Skill):
    """静如止水 — Skip the opponent's next turn."""

    def __init__(self) -> None:
        super().__init__(
            name="静如止水",
            description="使对手下一回合无法落子。",
            cooldown_turns=7,
            initial_cooldown=0,
        )

    def apply(self, game: "Game", player: "Player", rng: random.Random) -> SkillResult:
        game.schedule_skip_for(player.opponent)
        opponent_label = game.player_label(player.opponent)
        return SkillResult(
            skill_name=self.name,
            player_name=player.name,
            description=f"{opponent_label} 的下一回合将被跳过",
            details={"skipped": player.opponent.name},
        )


class MightyClearingSkill(Skill):
    """力拔山兮 — Clear the entire board."""

    def __init__(self) -> None:
        super().__init__(
            name="力拔山兮",
            description="清空棋盘上全部棋子。",
            cooldown_turns=12,
            initial_cooldown=7,
        )

    def apply(self, game: "Game", player: "Player", rng: random.Random) -> SkillResult:
        game.board.clear()
        game.last_move = None
        game.winner = None
        game.draw = False
        return SkillResult(
            skill_name=self.name,
            player_name=player.name,
            description="棋盘被全部清空",
            details={},
        )


class SeizeAndMoveSkill(Skill):
    """擒擒拿拿 — Relocate an opponent stone to a different empty cell."""

    def __init__(self) -> None:
        super().__init__(
            name="擒擒拿拿",
            description="将对手的一枚棋子搬运到新的位置。",
            cooldown_turns=9,
            initial_cooldown=3,
        )

    def apply(self, game: "Game", player: "Player", rng: random.Random) -> SkillResult:
        source = game.cursor
        if game.board.get(source) != player.opponent.stone:
            raise ValueError("光标需要停在对手的棋子上才能使用擒擒拿拿")

        target = self._find_target(game, source, rng)
        if target is None:
            raise ValueError("棋盘上没有可供移动的空位")

        stone = game.board.remove_stone(source)
        if game.last_move and game.last_move.coordinate == source:
            game.last_move = None

        produced_win = game.board.place_stone(target, stone)
        if produced_win:
            winning_player = player.opponent
            game.winner = winning_player
            game.draw = False
            game.last_move = None
            victory_note = f"{game.player_label(winning_player)} 因棋子搬运达成五连珠"
            game._log_action(victory_note)
            game.push_status_message(victory_note)
            game._comment_victory(winning_player)

        return SkillResult(
            skill_name=self.name,
            player_name=player.name,
            description=f"搬运了对手棋子：{source} -> {target}",
            details={"from": source, "to": target},
        )

    @staticmethod
    def _find_target(game: "Game", source: Coordinate, rng: random.Random) -> Coordinate | None:
        empties: List[Coordinate] = []
        for row in range(game.board.size):
            for col in range(game.board.size):
                coord = (row, col)
                if coord == source:
                    continue
                if game.board.is_empty(coord):
                    empties.append(coord)
        if not empties:
            return None
        return rng.choice(empties)


ALL_SKILLS: Dict[str, Skill] = {
    skill.name: skill
    for skill in (
        StoneStormSkill(),
        StillWatersSkill(),
        MightyClearingSkill(),
        SeizeAndMoveSkill(),
    )
}

SKILL_HOTKEYS: Dict[str, str] = {
    "飞沙走石": "1",
    "静如止水": "2",
    "力拔山兮": "3",
    "擒擒拿拿": "4",
}
