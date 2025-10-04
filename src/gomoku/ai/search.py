"""Search utilities for deciding AI moves."""

from __future__ import annotations

import copy
import heapq
import math
import random
from dataclasses import dataclass, field
from typing import Iterable, List, Optional, Sequence, Tuple

from ..board import Coordinate
from ..config import EMPTY_CELL, WIN_SEQUENCE_LENGTH
from ..game import Game, Player
from ..skills import ALL_SKILLS

Grid = Tuple[Tuple[str, ...], ...]
Direction = Tuple[int, int]

_DIRECTIONS: Tuple[Direction, ...] = ((1, 0), (0, 1), (1, 1), (1, -1))
_MAX_EXPANSIONS = 5000
_MAX_STONESTORM_BRANCHES = 3
_STONE_STORM = "飞沙走石"
_STILL_WATERS = "静如止水"
_SEIZE_AND_MOVE = "擒擒拿拿"
_MIGHTY_CLEARING = "力拔山兮"
_PLAYER_INDEX = {
    Player.BLACK: 0,
    Player.WHITE: 1,
}


@dataclass(frozen=True)
class _CooldownState:
    skill_names: Tuple[str, ...]
    values: Tuple[Tuple[int, ...], ...]
    round_number: int

    @classmethod
    def from_game(cls, game: Game, skill_names: Tuple[str, ...]) -> "_CooldownState":
        values = tuple(
            tuple(game.skill_cooldowns[player].get(name, 0) for name in skill_names)
            for player in Player
        )
        return cls(skill_names=skill_names, values=values, round_number=len(game.board.history))

    def for_player(self, player: Player) -> Tuple[int, ...]:
        return self.values[_PLAYER_INDEX[player]]

    def advance_after_move(self, player: Player) -> "_CooldownState":
        next_values = list(self.values)
        opponent_index = _PLAYER_INDEX[player.opponent]
        opponent_cooldowns = tuple(
            cooldown - 1 if cooldown > 0 else 0
            for cooldown in self.values[opponent_index]
        )
        next_values[opponent_index] = opponent_cooldowns
        return _CooldownState(
            skill_names=self.skill_names,
            values=tuple(next_values),
            round_number=self.round_number + 1,
        )

    def with_skill_triggered(self, player: Player, skill_name: str, cooldown_turns: int) -> "_CooldownState":
        try:
            skill_index = self.skill_names.index(skill_name)
        except ValueError as exc:  # pragma: no cover - defensive guard
            raise KeyError(f"Unknown skill: {skill_name}") from exc

        next_values = [list(cooldowns) for cooldowns in self.values]
        next_values[_PLAYER_INDEX[player]][skill_index] = cooldown_turns
        return _CooldownState(
            skill_names=self.skill_names,
            values=tuple(tuple(cooldowns) for cooldowns in next_values),
            round_number=self.round_number,
        )


@dataclass(order=True)
class _SearchNode:
    priority: float
    g_cost: int
    grid: Grid
    player_to_move: Player
    first_action: "SearchAction" = field(compare=False)
    evaluation: float
    is_terminal: bool
    cooldown_state: _CooldownState


@dataclass(frozen=True)
class SearchAction:
    move: Optional[Coordinate] = None
    skill: Optional[str] = None
    skill_target: Optional[Coordinate] = None

    def __post_init__(self) -> None:
        move_set = self.move is not None
        skill_set = self.skill is not None
        if move_set == skill_set:
            raise ValueError("SearchAction must define exactly one of move or skill")
        if not move_set and self.skill == _STONE_STORM and self.skill_target is None:
            raise ValueError("StoneStorm actions require a target coordinate")


def choose_move(game: Game, depth: int, rng: Optional[random.Random] = None) -> Coordinate:
    """Compatibility wrapper returning a coordinate move when selected by the search."""

    action = choose_action(game, depth, rng=rng)
    if action.move is None:
        raise ValueError("Search selected a skill action; use choose_action for full context")
    return action.move


def choose_action(game: Game, depth: int, rng: Optional[random.Random] = None) -> SearchAction:
    """Return the best action (move or skill) for the current player."""

    if depth < 1:
        depth = 1
    rng = rng or game.rng
    grid = _grid_from_board(game)
    current_player = game.current_player
    skill_order = _skill_order(game)
    root_cooldowns = _CooldownState.from_game(game, skill_order)
    candidate_moves = list(_candidate_moves(grid))
    skill_children = list(_root_skill_simulations(game, root_cooldowns, rng))
    if not candidate_moves and not skill_children:
        raise ValueError("No legal moves or skills available")

    open_nodes: List[_SearchNode] = []
    best_score = -math.inf
    best_actions: List[SearchAction] = []

    def record_candidate(score: float, action: SearchAction) -> None:
        nonlocal best_score, best_actions
        if score > best_score:
            best_score = score
            best_actions = [action]
        elif math.isclose(score, best_score, rel_tol=1e-9, abs_tol=1e-6):
            best_actions.append(action)

    for move in candidate_moves:
        next_grid, win = _apply_move(grid, move, current_player.stone)
        evaluation = _static_evaluation(next_grid, current_player)
        is_terminal = win or _is_draw(next_grid)
        priority = _priority(1, evaluation, current_player.opponent, current_player)
        action = SearchAction(move=move)
        node = _SearchNode(
            priority=priority,
            g_cost=1,
            grid=next_grid,
            player_to_move=current_player.opponent,
            first_action=action,
            evaluation=evaluation,
            is_terminal=is_terminal,
            cooldown_state=root_cooldowns.advance_after_move(current_player),
        )
        heapq.heappush(open_nodes, node)
        if is_terminal:
            record_candidate(evaluation, action)

    for action, sim_game, sim_cooldowns in skill_children:
        next_grid = _grid_from_board(sim_game)
        evaluation = _static_evaluation(next_grid, current_player)
        is_terminal = sim_game.is_finished
        priority = _priority(1, evaluation, sim_game.current_player, current_player)
        node = _SearchNode(
            priority=priority,
            g_cost=1,
            grid=next_grid,
            player_to_move=sim_game.current_player,
            first_action=action,
            evaluation=evaluation,
            is_terminal=is_terminal,
            cooldown_state=sim_cooldowns,
        )
        heapq.heappush(open_nodes, node)
        if is_terminal:
            record_candidate(evaluation, action)

    expansions = 0
    while open_nodes and expansions < _MAX_EXPANSIONS:
        node = heapq.heappop(open_nodes)
        expansions += 1

        if node.is_terminal or node.g_cost >= depth:
            score = node.evaluation
            if node.is_terminal:
                parity = node.g_cost % 2
                if parity == 1 and score < 0:
                    score = -score
                if parity == 0 and score > 0:
                    score = -score
            record_candidate(score, node.first_action)
            continue

        next_moves = list(_candidate_moves(node.grid))
        if not next_moves:
            record_candidate(node.evaluation, node.first_action)
            continue

        for move in next_moves:
            stone = node.player_to_move.stone
            next_grid, win = _apply_move(node.grid, move, stone)
            evaluation = _static_evaluation(next_grid, current_player)
            is_terminal = win or _is_draw(next_grid)
            g_cost = node.g_cost + 1
            next_cooldowns = node.cooldown_state.advance_after_move(node.player_to_move)
            priority = _priority(g_cost, evaluation, node.player_to_move.opponent, current_player)
            heapq.heappush(
                open_nodes,
                _SearchNode(
                    priority=priority,
                    g_cost=g_cost,
                    grid=next_grid,
                    player_to_move=node.player_to_move.opponent,
                    first_action=node.first_action,
                    evaluation=evaluation,
                    is_terminal=is_terminal,
                    cooldown_state=next_cooldowns,
                ),
            )

    if not best_actions:
        if candidate_moves:
            return SearchAction(move=rng.choice(candidate_moves))
        if skill_children:
            return rng.choice([child[0] for child in skill_children])
        raise ValueError("Search failed to identify a viable action")

    return rng.choice(best_actions)


def _root_skill_simulations(
    game: Game,
    cooldown_state: _CooldownState,
    rng: Optional[random.Random],
) -> List[Tuple[SearchAction, Game, _CooldownState]]:
    if rng is None:
        rng = game.rng

    results: List[Tuple[SearchAction, Game, _CooldownState]] = []
    for skill_name in _ready_skill_names(game):
        if skill_name == _MIGHTY_CLEARING:
            continue

        if skill_name == _STONE_STORM:
            results.extend(
                _stone_storm_simulations(game, cooldown_state, rng)
            )
            continue

        try:
            simulated_game, simulated_state = _simulate_skill_effect(
                game,
                cooldown_state,
                skill_name,
                rng,
            )
        except ValueError:
            continue

        skill_target: Optional[Coordinate] = None
        if (
            skill_name == _SEIZE_AND_MOVE
            and simulated_game.last_skill
            and isinstance(simulated_game.last_skill.details.get("from"), Sequence)
        ):
            source = simulated_game.last_skill.details["from"]
            if isinstance(source, Sequence) and len(source) == 2:
                skill_target = (int(source[0]), int(source[1]))

        action = SearchAction(skill=skill_name, skill_target=skill_target)
        results.append((action, simulated_game, simulated_state))

    return results


def _ready_skill_names(game: Game) -> Iterable[str]:
    cooldowns = game.skill_cooldowns[game.current_player]
    for name in game.skill_registry:
        if cooldowns.get(name, 0) == 0:
            yield name


def _stone_storm_simulations(
    game: Game,
    cooldown_state: _CooldownState,
    rng: random.Random,
) -> List[Tuple[SearchAction, Game, _CooldownState]]:
    opponent = game.current_player.opponent
    opponent_coords = list(game.occupied_by_player(opponent))
    if not opponent_coords:
        return []

    cursor_target = None
    if game.board.get(game.cursor) == opponent.stone:
        cursor_target = game.cursor

    ordered_targets: List[Coordinate] = []
    if cursor_target is not None:
        ordered_targets.append(cursor_target)
    ordered_targets.extend(coord for coord in opponent_coords if coord != cursor_target)

    scored: List[Tuple[float, Coordinate, Game, _CooldownState]] = []
    for target in ordered_targets:
        try:
            simulated_game, simulated_state = _simulate_skill_effect(
                game,
                cooldown_state,
                _STONE_STORM,
                rng,
                skill_target=target,
            )
        except ValueError:
            continue
        evaluation = _static_evaluation(
            _grid_from_board(simulated_game),
            game.current_player,
        )
        scored.append((evaluation, target, simulated_game, simulated_state))

    scored.sort(key=lambda item: item[0], reverse=True)
    limited = scored[:_MAX_STONESTORM_BRANCHES]
    results: List[Tuple[SearchAction, Game, _CooldownState]] = []
    for _, target, sim_game, sim_state in limited:
        results.append(
            (
                SearchAction(skill=_STONE_STORM, skill_target=target),
                sim_game,
                sim_state,
            )
        )
    return results


def _skill_order(game: Game) -> Tuple[str, ...]:
    if game.skill_registry:
        return tuple(game.skill_registry.keys())
    # Fallback to default ordering when registry is empty.
    return tuple(ALL_SKILLS.keys())


def _simulate_skill_effect(
    game: Game,
    cooldown_state: _CooldownState,
    skill_name: str,
    rng: Optional[random.Random] = None,
    *,
    skill_target: Optional[Coordinate] = None,
) -> Tuple[Game, _CooldownState]:
    """Return a simulated game clone and updated cooldown state after using ``skill_name``.

    The original ``game`` remains untouched. Cooldowns are updated in the same sequence as
    :meth:`Game.use_skill`, including resetting the skill and advancing the round.
    """

    if skill_name not in game.skill_registry:
        raise KeyError(f"Unknown skill: {skill_name}")

    simulated_game = copy.deepcopy(game)
    simulated_game.rng = copy.deepcopy(rng) if rng is not None else random.Random()
    if skill_target is not None:
        simulated_game.set_cursor(skill_target)
    simulated_game.use_skill(skill_name)
    updated_state = _CooldownState.from_game(simulated_game, cooldown_state.skill_names)
    return simulated_game, updated_state


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