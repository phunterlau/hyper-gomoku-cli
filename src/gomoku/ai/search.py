"""Search utilities for deciding AI moves."""

from __future__ import annotations

import heapq
import math
import random
from dataclasses import dataclass
from typing import Iterable, List, Optional, Tuple

from ..board import Coordinate
from ..config import EMPTY_CELL, WIN_SEQUENCE_LENGTH
from ..game import Game, Player

Grid = Tuple[Tuple[str, ...], ...]
Direction = Tuple[int, int]

_DIRECTIONS: Tuple[Direction, ...] = ((1, 0), (0, 1), (1, 1), (1, -1))
_MAX_EXPANSIONS = 5000


@dataclass(order=True)
class _SearchNode:
    priority: float
    g_cost: int
    grid: Grid
    player_to_move: Player
    first_move: Coordinate
    evaluation: float
    is_terminal: bool


def choose_move(game: Game, depth: int, rng: Optional[random.Random] = None) -> Coordinate:
    """Return the coordinate selected by the AI using an A* search variant."""

    if depth < 1:
        depth = 1
    rng = rng or game.rng
    grid = _grid_from_board(game)
    current_player = game.current_player
    candidates = list(_candidate_moves(grid))
    if not candidates:
        raise ValueError("No legal moves available")
    if len(candidates) == 1:
        return candidates[0]

    open_nodes: List[_SearchNode] = []
    best_score = -math.inf
    best_moves: List[Coordinate] = []

    for move in candidates:
        next_grid, win = _apply_move(grid, move, current_player.stone)
        evaluation = _static_evaluation(next_grid, current_player)
        is_terminal = win or _is_draw(next_grid)
        priority = _priority(1, evaluation, current_player.opponent, current_player)
        node = _SearchNode(
            priority=priority,
            g_cost=1,
            grid=next_grid,
            player_to_move=current_player.opponent,
            first_move=move,
            evaluation=evaluation,
            is_terminal=is_terminal,
        )
        heapq.heappush(open_nodes, node)
        if is_terminal and evaluation > best_score:
            best_score = evaluation
            best_moves = [move]

    expansions = 0
    while open_nodes and expansions < _MAX_EXPANSIONS:
        node = heapq.heappop(open_nodes)
        expansions += 1

        if node.is_terminal or node.g_cost >= depth:
            score = node.evaluation
            if node.is_terminal:
                # Encourage immediate wins and discourage losses.
                parity = node.g_cost % 2
                if parity == 1 and score < 0:
                    score = -score
                if parity == 0 and score > 0:
                    score = -score
            if score > best_score:
                best_score = score
                best_moves = [node.first_move]
            elif math.isclose(score, best_score, rel_tol=1e-9, abs_tol=1e-6):
                best_moves.append(node.first_move)
            continue

        next_moves = list(_candidate_moves(node.grid))
        if not next_moves:
            score = node.evaluation
            if score > best_score:
                best_score = score
                best_moves = [node.first_move]
            elif math.isclose(score, best_score, rel_tol=1e-9, abs_tol=1e-6):
                best_moves.append(node.first_move)
            continue

        for move in next_moves:
            stone = node.player_to_move.stone
            next_grid, win = _apply_move(node.grid, move, stone)
            evaluation = _static_evaluation(next_grid, current_player)
            is_terminal = win or _is_draw(next_grid)
            g_cost = node.g_cost + 1
            priority = _priority(g_cost, evaluation, node.player_to_move.opponent, current_player)
            heapq.heappush(
                open_nodes,
                _SearchNode(
                    priority=priority,
                    g_cost=g_cost,
                    grid=next_grid,
                    player_to_move=node.player_to_move.opponent,
                    first_move=node.first_move,
                    evaluation=evaluation,
                    is_terminal=is_terminal,
                ),
            )

    if not best_moves:
        return rng.choice(candidates)
    return rng.choice(best_moves)


def _grid_from_board(game: Game) -> Grid:
    return tuple(tuple(cell for cell in row) for row in game.board.grid)


def _candidate_moves(grid: Grid) -> Iterable[Coordinate]:
    size = len(grid)
    occupied: List[Coordinate] = []
    for row in range(size):
        for col in range(size):
            if grid[row][col] != EMPTY_CELL:
                occupied.append((row, col))
    if not occupied:
        center = size // 2
        yield (center, center)
        return

    seen: set[Coordinate] = set()
    for row, col in occupied:
        for d_row in range(-2, 3):
            for d_col in range(-2, 3):
                if d_row == 0 and d_col == 0:
                    continue
                nr, nc = row + d_row, col + d_col
                if 0 <= nr < size and 0 <= nc < size and grid[nr][nc] == EMPTY_CELL:
                    coord = (nr, nc)
                    if coord not in seen:
                        seen.add(coord)
                        yield coord

    if not seen:
        for row in range(size):
            for col in range(size):
                if grid[row][col] == EMPTY_CELL:
                    yield (row, col)


def _apply_move(grid: Grid, coord: Coordinate, stone: str) -> Tuple[Grid, bool]:
    row, col = coord
    if grid[row][col] != EMPTY_CELL:
        raise ValueError(f"坐标 {coord} 已经有棋子了")
    mutable = [list(row_values) for row_values in grid]
    mutable[row][col] = stone
    new_grid = tuple(tuple(row_values) for row_values in mutable)
    win = _forms_winning_sequence(new_grid, coord, stone)
    return new_grid, win


def _forms_winning_sequence(grid: Grid, coord: Coordinate, stone: str) -> bool:
    return any(_line_length(grid, coord, stone, delta) >= WIN_SEQUENCE_LENGTH for delta in _DIRECTIONS)


def _line_length(grid: Grid, coord: Coordinate, stone: str, delta: Direction) -> int:
    total = 1
    total += _count_in_direction(grid, coord, stone, delta)
    total += _count_in_direction(grid, coord, stone, (-delta[0], -delta[1]))
    return total


def _count_in_direction(grid: Grid, coord: Coordinate, stone: str, delta: Direction) -> int:
    count = 0
    row, col = coord
    dr, dc = delta
    size = len(grid)
    while True:
        row += dr
        col += dc
        if not (0 <= row < size and 0 <= col < size):
            break
        if grid[row][col] != stone:
            break
        count += 1
    return count


def _is_draw(grid: Grid) -> bool:
    return all(cell != EMPTY_CELL for row in grid for cell in row)


def _static_evaluation(grid: Grid, perspective: Player) -> float:
    opponent = perspective.opponent
    perspective_score = _score_for_player(grid, perspective)
    opponent_score = _score_for_player(grid, opponent)
    return perspective_score - opponent_score


def _score_for_player(grid: Grid, player: Player) -> float:
    stone = player.stone
    size = len(grid)
    total = 0.0
    for row in range(size):
        for col in range(size):
            if grid[row][col] != stone:
                continue
            for delta in _DIRECTIONS:
                prev_row = row - delta[0]
                prev_col = col - delta[1]
                if 0 <= prev_row < size and 0 <= prev_col < size and grid[prev_row][prev_col] == stone:
                    continue
                length, open_ends = _sequence_metrics(grid, (row, col), stone, delta)
                total += _sequence_score(length, open_ends)
    return total


def _sequence_metrics(grid: Grid, coord: Coordinate, stone: str, delta: Direction) -> Tuple[int, int]:
    length = 0
    open_ends = 0
    size = len(grid)
    row, col = coord

    dr, dc = delta
    # forward direction
    while 0 <= row < size and 0 <= col < size and grid[row][col] == stone:
        length += 1
        row += dr
        col += dc
    if 0 <= row < size and 0 <= col < size and grid[row][col] == EMPTY_CELL:
        open_ends += 1

    # backward direction
    row, col = coord
    br, bc = -dr, -dc
    row += br
    col += bc
    while 0 <= row < size and 0 <= col < size and grid[row][col] == stone:
        length += 1
        row += br
        col += bc
    if 0 <= row < size and 0 <= col < size and grid[row][col] == EMPTY_CELL:
        open_ends += 1

    return length, open_ends


def _sequence_score(length: int, open_ends: int) -> float:
    if length >= WIN_SEQUENCE_LENGTH:
        return 1_000_000.0
    if length == WIN_SEQUENCE_LENGTH - 1:
        return 50_000.0 if open_ends == 2 else 5_000.0
    if length == WIN_SEQUENCE_LENGTH - 2:
        return 2_000.0 if open_ends == 2 else 400.0
    if length == WIN_SEQUENCE_LENGTH - 3:
        return 200.0 if open_ends == 2 else 50.0
    if length == 2:
        return 30.0 if open_ends == 2 else 10.0
    return 1.0


def _priority(g_cost: int, evaluation: float, player_to_move: Player, root_player: Player) -> float:
    sign = 1.0 if player_to_move == root_player else -1.0
    return g_cost - sign * evaluation