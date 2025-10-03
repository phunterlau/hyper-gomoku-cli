"""Game engine for Gomoku turn management and rules enforcement."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Iterable, List, Optional, Tuple

from .board import Board, Coordinate
from .config import BLACK_STONE, BOARD_SIZE, WHITE_STONE
from .skills import ALL_SKILLS, Skill, SkillResult
from .commentary import Commentator


class Player(Enum):
    BLACK = "black"
    WHITE = "white"

    @property
    def stone(self) -> str:
        return BLACK_STONE if self is Player.BLACK else WHITE_STONE

    @property
    def opponent(self) -> "Player":
        return Player.WHITE if self is Player.BLACK else Player.BLACK


PLAYER_DEFAULT_ALIASES: Dict[Player, str] = {
    Player.BLACK: "黑方",
    Player.WHITE: "白方",
}


def player_default_alias(player: Player) -> str:
    return PLAYER_DEFAULT_ALIASES.get(player, player.name.title())


@dataclass
class MoveResult:
    coordinate: Coordinate
    player: Player
    stone: str
    produced_win: bool
    produced_draw: bool


@dataclass(frozen=True)
class SkillStatus:
    name: str
    description: str
    cooldown_remaining: int


@dataclass
class Game:
    """State manager for a two-player Gomoku match."""

    board: Board = field(default_factory=Board)
    current_player: Player = Player.BLACK
    cursor: Coordinate = field(default_factory=lambda: (BOARD_SIZE // 2, BOARD_SIZE // 2))
    last_move: Optional[MoveResult] = None
    last_skill: Optional[SkillResult] = None
    info_message: Optional[str] = None
    winner: Optional[Player] = None
    draw: bool = False
    rng: random.Random = field(default_factory=random.Random)
    skill_registry: Dict[str, Skill] = field(default_factory=lambda: dict(ALL_SKILLS))
    skip_next_player: Optional[Player] = None
    skipped_last_player: Optional[Player] = None
    action_log: List[str] = field(default_factory=list)
    _log_capacity: int = 16
    status_messages: List[str] = field(default_factory=lambda: [
        "欢迎来到技能五子棋学校！",
        "老师你好像快输了。",
        "技能准备好了吗？",
    ])
    overlay_lines: Optional[List[str]] = None
    commentator: Optional[Commentator] = None
    player_aliases: Dict[Player, str] = field(
        default_factory=lambda: dict(PLAYER_DEFAULT_ALIASES)
    )
    skill_cooldowns: Dict[Player, Dict[str, int]] = field(init=False)

    @classmethod
    def new(cls, *, rng: Optional[random.Random] = None) -> "Game":
        return cls(rng=rng or random.Random())

    def __post_init__(self) -> None:  # pragma: no cover - simple initialization
        self.skill_cooldowns = {
            player: {
                name: skill.initial_cooldown
                for name, skill in self.skill_registry.items()
            }
            for player in Player
        }
        self._ensure_status_length()
        self.ensure_commentator()

    # ------------------------------------------------------------------
    # Move application
    # ------------------------------------------------------------------
    def place_at_cursor(self) -> MoveResult:
        """Attempt to place the current player's stone at the cursor."""

        result = self.place_stone(self.cursor)
        return result

    def place_stone(self, coord: Coordinate) -> MoveResult:
        if self.is_finished:
            raise ValueError("对局已经结束")

        stone = self.current_player.stone
        produced_win = self.board.place_stone(coord, stone)
        produced_draw = not produced_win and self.board.is_full()

        if produced_win:
            self.winner = self.current_player
            self._comment_victory(self.current_player)
        elif produced_draw:
            self.draw = True
            self._comment_draw()

        result = MoveResult(
            coordinate=coord,
            player=self.current_player,
            stone=stone,
            produced_win=produced_win,
            produced_draw=produced_draw,
        )
        self.last_move = result
        self.last_skill = None
        self.info_message = None
        coord_label = self._coord_label(coord)
        actor_label = self.player_label(self.current_player)
        self._log_action(f"{actor_label} 落子于 {coord_label}")
        self.push_status_message(f"{actor_label} 落子于 {coord_label}")
        self._comment_move(coord)

        if not self.is_finished:
            self._advance_after_action()

        return result

    def use_skill(self, skill_name: str) -> SkillResult:
        if self.is_finished:
            raise ValueError("对局已经结束")

        skill = self.skill_registry.get(skill_name)
        if skill is None:
            raise ValueError(f"未知技能：{skill_name}")

        remaining = self.skill_cooldowns[self.current_player][skill.name]
        if remaining > 0:
            raise ValueError(
                f"技能「{skill.name}」还需 {remaining} 回合冷却"
            )

        result = skill.apply(self, self.current_player, self.rng)
        self.skill_cooldowns[self.current_player][skill.name] = skill.cooldown_turns
        self.last_skill = result
        self.info_message = result.description
        actor_label = self.player_label(self.current_player)
        self._log_action(f"{actor_label} 使用了 {skill.name}（{result.description}）")
        self.push_status_message(result.description)
        self._comment_skill(skill.name)
        if not self.is_finished:
            self._advance_after_action()
        return result

    # ------------------------------------------------------------------
    # Cursor management
    # ------------------------------------------------------------------
    def move_cursor(self, delta_row: int, delta_col: int) -> Coordinate:
        row, col = self.cursor
        new_row = (row + delta_row) % self.board.size
        new_col = (col + delta_col) % self.board.size
        self.cursor = (new_row, new_col)
        return self.cursor

    def set_cursor(self, coord: Coordinate) -> None:
        if not self.board.is_within_bounds(coord):
            raise ValueError("光标坐标超出棋盘范围")
        self.cursor = coord

    # ------------------------------------------------------------------
    # Status helpers
    # ------------------------------------------------------------------
    @property
    def is_finished(self) -> bool:
        return self.winner is not None or self.draw

    def status_message(self) -> str:
        if self.winner:
            return f"{self.player_label(self.winner)} 获胜！"
        if self.draw:
            return "平局"
        if self.skipped_last_player:
            return f"{self.player_label(self.skipped_last_player)} 已被跳过！"
        if self.skip_next_player:
            return f"{self.player_label(self.skip_next_player)} 将在下一回合被跳过"
        return f"{self.player_label(self.current_player)} 的回合"

    def set_player_alias(self, player: Player, alias: str) -> None:
        cleaned = alias.strip() if alias else ""
        self.player_aliases[player] = cleaned or player_default_alias(player)

    def player_alias(self, player: Player) -> str:
        return self.player_aliases.get(player, player_default_alias(player))

    def player_label(self, player: Player) -> str:
        return f"{self.player_alias(player)} ({player.stone})"

    def occupied_by_player(self, player: Player) -> Iterable[Coordinate]:
        stone = player.stone
        return (coord for coord in self.board.occupied_cells() if self.board.get(coord) == stone)

    def skill_status(self, player: Player) -> List[SkillStatus]:
        return [
            SkillStatus(
                name=name,
                description=skill.description,
                cooldown_remaining=self.skill_cooldowns[player][name],
            )
            for name, skill in self.skill_registry.items()
        ]

    def schedule_skip_for(self, player: Player) -> None:
        self.skip_next_player = player
        message = f"{self.player_label(player)} 将在下一回合被跳过"
        self.info_message = message
        self._log_action(message)
        self.push_status_message(self.info_message)

    def reset(self) -> None:
        self.board.clear()
        self.current_player = Player.BLACK
        self.cursor = (BOARD_SIZE // 2, BOARD_SIZE // 2)
        self.last_move = None
        self.last_skill = None
        self.info_message = None
        self.winner = None
        self.draw = False
        self.skip_next_player = None
        self.skipped_last_player = None
        for player in Player:
            for name, skill in self.skill_registry.items():
                self.skill_cooldowns[player][name] = skill.initial_cooldown
        self.action_log.clear()
        self._log_action("对局已重置")
        self.status_messages = self._default_status_messages()
        self.overlay_lines = None
        self.ensure_commentator()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _advance_after_action(self) -> None:
        next_player = self.current_player.opponent
        self._move_to_player(next_player)

    def _move_to_player(self, player: Player) -> None:
        skipped = False
        while True:
            self.current_player = player
            self._tick_cooldowns(player)
            if self.skip_next_player is player:
                self.skip_next_player = None
                self.skipped_last_player = player
                skipped_message = f"{self.player_label(player)} 已被跳过！"
                self.info_message = skipped_message
                self._log_action(skipped_message)
                self.push_status_message(self.info_message)
                player = player.opponent
                skipped = True
                continue
            if not skipped:
                self.skipped_last_player = None
            break

    def _tick_cooldowns(self, player: Player) -> None:
        for name, remaining in self.skill_cooldowns[player].items():
            if remaining > 0:
                self.skill_cooldowns[player][name] = remaining - 1

    # ------------------------------------------------------------------
    # Action logging helpers
    # ------------------------------------------------------------------
    def _log_action(self, message: str) -> None:
        self.action_log.append(message)
        if len(self.action_log) > self._log_capacity:
            del self.action_log[0 : len(self.action_log) - self._log_capacity]

    @staticmethod
    def _coord_label(coord: Coordinate) -> str:
        row, col = coord
        col_label = chr(ord("A") + col)
        return f"{col_label}{row}"

    def push_status_message(self, message: str) -> None:
        sanitized = self._sanitize_status_line(message)
        if not sanitized:
            return
        self.status_messages.append(sanitized)
        if len(self.status_messages) > 3:
            self.status_messages = self.status_messages[-3:]

    def set_status_messages(self, messages: Iterable[str]) -> None:
        sanitized = [self._sanitize_status_line(msg) for msg in messages]
        sanitized = [msg for msg in sanitized if msg]
        self.status_messages = self._pad_status_messages(sanitized)

    def _sanitize_status_line(self, message: Optional[str]) -> str:
        if not message:
            return ""
        return str(message).strip()

    def _ensure_status_length(self) -> None:
        self.status_messages = self._pad_status_messages(self.status_messages)

    def _pad_status_messages(self, messages: Iterable[str]) -> List[str]:
        sanitized = list(messages)[:3]
        while len(sanitized) < 3:
            sanitized.insert(0, "")
        return sanitized[-3:]

    def _default_status_messages(self) -> List[str]:
        return [
            "欢迎来到技能五子棋学校！",
            "老师你好像快输了。",
            "技能准备好了吗？",
        ]

    # ------------------------------------------------------------------
    # Overlay helpers
    # ------------------------------------------------------------------
    def show_overlay(self, lines: Iterable[str]) -> None:
        prepared = [self._sanitize_status_line(line) or " " for line in lines]
        self.overlay_lines = prepared or [" "]

    def clear_overlay(self) -> None:
        self.overlay_lines = None

    def ensure_commentator(self) -> Commentator:
        if self.commentator is None:
            self.commentator = Commentator(self.rng)
        return self.commentator

    def _comment_move(self, coord: Coordinate) -> None:
        commentator = self.ensure_commentator()
        message = commentator.comment_on_move(self, coord)
        self.push_status_message(message)

    def _comment_skill(self, skill_name: str) -> None:
        commentator = self.ensure_commentator()
        message = commentator.comment_on_skill(skill_name)
        self.push_status_message(message)

    def _comment_victory(self, winner: Player) -> None:
        commentator = self.ensure_commentator()
        key = "victory_black" if winner is Player.BLACK else "victory_white"
        lines = commentator.comment_on_overlay(key)
        self.show_overlay(lines)
        if lines:
            self.push_status_message(lines[0])

    def _comment_draw(self) -> None:
        commentator = self.ensure_commentator()
        lines = commentator.comment_on_overlay("draw")
        self.show_overlay(lines)
        if lines:
            self.push_status_message(lines[0])
