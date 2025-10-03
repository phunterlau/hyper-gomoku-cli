"""Board model and helper functions for Gomoku."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List, Optional, Tuple

from .config import BOARD_SIZE, EMPTY_CELL, WIN_SEQUENCE_LENGTH

Coordinate = Tuple[int, int]
MoveRecord = Tuple[str, Coordinate]

_DIRECTIONS: Tuple[Coordinate, ...] = ((1, 0), (0, 1), (1, 1), (1, -1))


@dataclass
class Board:
    """Represents a 2D Gomoku board with win detection and history tracking."""

    size: int = BOARD_SIZE
    win_length: int = WIN_SEQUENCE_LENGTH
    grid: List[List[str]] = field(init=False)
    history: List[MoveRecord] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.size <= 0:
            raise ValueError("棋盘大小必须为正数")
        if self.win_length <= 1:
            raise ValueError("连珠长度必须大于 1")
        self.grid = [[EMPTY_CELL for _ in range(self.size)] for _ in range(self.size)]

    # ---------------------------------------------------------------------
    # Query helpers
    # ---------------------------------------------------------------------
    def is_within_bounds(self, coord: Coordinate) -> bool:
        """Return ``True`` if the coordinate lies inside the board."""

        row, col = coord
        return 0 <= row < self.size and 0 <= col < self.size

    def get(self, coord: Coordinate) -> Optional[str]:
        """Return the stone at the coordinate or ``None`` when out of bounds."""

        if not self.is_within_bounds(coord):
            return None
        row, col = coord
        return self.grid[row][col]

    def is_empty(self, coord: Coordinate) -> bool:
        """Return ``True`` when the cell is empty."""

        value = self.get(coord)
        return value == EMPTY_CELL if value is not None else False

    def is_full(self) -> bool:
        """Return ``True`` when no empty cells remain on the board."""

        return all(cell != EMPTY_CELL for row in self.grid for cell in row)

    def occupied_cells(self) -> Iterable[Coordinate]:
        """Iterate over coordinates currently holding stones."""

        for row_idx, row in enumerate(self.grid):
            for col_idx, cell in enumerate(row):
                if cell != EMPTY_CELL:
                    yield (row_idx, col_idx)

    # ---------------------------------------------------------------------
    # Mutation helpers
    # ---------------------------------------------------------------------
    def place_stone(self, coord: Coordinate, stone: str) -> bool:
        """Place ``stone`` at ``coord``.

        Returns ``True`` if the move completes a winning sequence, otherwise
        ``False``. Raises :class:`ValueError` for invalid coordinates, empty
        stone markers, or when attempting to occupy a filled cell.
        """

        if not stone or stone == EMPTY_CELL:
            raise ValueError("棋子符号不能为空，也不能与空位标记相同")
        if not self.is_within_bounds(coord):
            raise ValueError(f"坐标 {coord} 超出棋盘范围")
        if not self.is_empty(coord):
            raise ValueError(f"坐标 {coord} 已经有棋子了")

        row, col = coord
        self.grid[row][col] = stone
        self.history.append((stone, coord))
        return self._forms_winning_line(coord, stone)

    def remove_stone(self, coord: Coordinate) -> str:
        """Remove the stone at ``coord`` and return it.

        Raises :class:`ValueError` when the coordinate is out of bounds or empty.
        The move history is updated accordingly.
        """

        if not self.is_within_bounds(coord):
            raise ValueError(f"坐标 {coord} 超出棋盘范围")

        row, col = coord
        stone = self.grid[row][col]
        if stone == EMPTY_CELL:
            raise ValueError(f"坐标 {coord} 上没有棋子")

        self.grid[row][col] = EMPTY_CELL
        for index in range(len(self.history) - 1, -1, -1):
            if self.history[index][1] == coord:
                self.history.pop(index)
                break
        return stone

    def undo_last_move(self) -> MoveRecord:
        """Pop and return the most recent move, clearing its cell."""

        if not self.history:
            raise ValueError("没有可以悔棋的落子记录")

        stone, coord = self.history.pop()
        row, col = coord
        self.grid[row][col] = EMPTY_CELL
        return stone, coord

    def clear(self) -> None:
        """Reset the board to its initial empty state."""

        for row in self.grid:
            for col in range(self.size):
                row[col] = EMPTY_CELL
        self.history.clear()

    # ---------------------------------------------------------------------
    # Win detection
    # ---------------------------------------------------------------------
    def forms_winning_sequence(self, coord: Coordinate) -> bool:
        """Return ``True`` if the most recent stone at ``coord`` wins the game."""

        stone = self.get(coord)
        if stone is None or stone == EMPTY_CELL:
            return False
        return self._forms_winning_line(coord, stone)

    def _forms_winning_line(self, coord: Coordinate, stone: str) -> bool:
        return any(
            self._line_length(coord, stone, delta) >= self.win_length for delta in _DIRECTIONS
        )

    def _line_length(self, coord: Coordinate, stone: str, delta: Coordinate) -> int:
        total = 1  # include the stone at coord
        total += self._count_in_direction(coord, stone, delta)
        total += self._count_in_direction(coord, stone, (-delta[0], -delta[1]))
        return total

    def _count_in_direction(self, coord: Coordinate, stone: str, delta: Coordinate) -> int:
        count = 0
        row, col = coord
        d_row, d_col = delta
        while True:
            row += d_row
            col += d_col
            if not self.is_within_bounds((row, col)):
                break
            if self.grid[row][col] != stone:
                break
            count += 1
        return count
