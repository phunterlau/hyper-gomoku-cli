"""Rendering helpers for the terminal UI."""

from __future__ import annotations

from typing import Iterable, List, Set

from ..config import BLACK_STONE, BOARD_SIZE, EMPTY_CELL, WHITE_STONE
from ..game import Game, Player, SkillStatus
from ..skills import SKILL_HOTKEYS
from .overlay import OverlayManager
from .status_box import StatusBox
from .text_utils import display_width, pad_to_width

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
FG_CYAN = "\033[36m"
FG_YELLOW = "\033[33m"
FG_GREEN = "\033[32m"
FG_RED = "\033[31m"
FG_MAGENTA = "\033[35m"
FG_BLUE = "\033[34m"
FG_WHITE = "\033[37m"

STATUS_BOX = StatusBox()
OVERLAY = OverlayManager()

CELL_SEP = " "
CURSOR_MARKER = "▣"
ROW_LABELS = [f"{i:2d}" for i in range(BOARD_SIZE)]
COL_LABELS = [chr(ord("A") + i) for i in range(BOARD_SIZE)]
NEIGHBOR_MARKER = "∙"
CURSOR_OCCUPIED_BLACK = "◉"
CURSOR_OCCUPIED_WHITE = "◎"


def render(game: Game) -> str:
    lines: List[str] = []
    lines.extend(_render_hud(game))
    board_lines = [_render_header()] + list(_render_board(game))
    board_width = max(display_width(line) for line in board_lines)
    log_lines = _render_action_log_panel(game, len(board_lines))

    grid_lines: List[str] = []
    for idx, board_line in enumerate(board_lines):
        log_line = log_lines[idx] if idx < len(log_lines) else ""
        padded_board = pad_to_width(board_line, board_width)
        combined = f"{padded_board}   {log_line}"
        grid_lines.append(combined.rstrip())

    lines.extend(grid_lines)

    controls_line = _render_controls_line()
    lines.append(controls_line)

    body_width = max(display_width(line) for line in (*grid_lines, controls_line)) if grid_lines else display_width(controls_line)
    status_lines = list(_render_status_box(game, body_width))
    if status_lines:
        status_width = max(display_width(line) for line in status_lines)
        body_width = max(body_width, status_width)
    lines.extend(status_lines)

    if game.overlay_lines:
        overlay_lines = OVERLAY.overlay.render(
            game.overlay_lines,
            body_width,
            len(lines),
        )
        lines = _combine_with_overlay(lines, overlay_lines)

    return "\n".join(lines)


def _render_header() -> str:
    return "    " + CELL_SEP.join(COL_LABELS)


def _render_board(game: Game) -> Iterable[str]:
    rows: List[str] = []
    cursor = game.cursor
    neighbors = _neighbor_empty_cells(game, cursor)
    cursor_row, cursor_col = cursor
    for row_idx in range(game.board.size):
        rendered_cells: List[str] = []
        for col_idx in range(game.board.size):
            coord = (row_idx, col_idx)
            cell = game.board.get(coord)
            if coord == (cursor_row, cursor_col):
                rendered_cells.append(_render_cursor_cell(cell))
            elif coord in neighbors:
                rendered_cells.append(_render_neighbor_cell(cell))
            else:
                rendered_cells.append(_render_cell(cell))
        display_row = ROW_LABELS[row_idx] + " " + CELL_SEP.join(rendered_cells)
        rows.append(display_row)
    return rows


def _render_hud(game: Game) -> Iterable[str]:
    info_message = game.info_message or "—"
    status_text = (
        f"轮到：{game.player_label(game.current_player)}"
        f" | 状态：{game.status_message()}"
        f" | 光标：{_format_cursor(game.cursor)}"
    )
    last_move = "—"
    if game.last_move:
        coord = game.last_move.coordinate
        last_move = f"{game.player_label(game.last_move.player)} {_format_cursor(coord)}"
    last_skill = "—"
    if game.last_skill:
        try:
            skill_player = Player[game.last_skill.player_name]
        except KeyError:
            skill_player = game.last_move.player if game.last_move else game.current_player
        last_skill = f"{game.player_label(skill_player)} 使用 {game.last_skill.skill_name}"
    summary_text = (
        f"信息：{info_message} | 上一手：{last_move} | 上一技能：{last_skill}"
    )
    skills_lines = _render_skill_summary(game)
    return [
        _color(status_text, BOLD, FG_CYAN),
        _color(summary_text, FG_YELLOW),
        *skills_lines,
    ]


def _render_skill_summary(game: Game) -> List[str]:
    header_text = "技能"
    header = _color(header_text, BOLD, FG_MAGENTA)
    black = _render_skill_segment(
        game, Player.BLACK, game.skill_status(Player.BLACK), game.current_player
    )
    white = _render_skill_segment(
        game, Player.WHITE, game.skill_status(Player.WHITE), game.current_player
    )
    indent = " " * display_width(f"{header_text} ")
    return [
        f"{header} {black}",
        f"{indent}{white}",
    ]


def _render_skill_segment(
    game: Game, player: Player, statuses: List[SkillStatus], active_player: Player
) -> str:
    is_active = player == active_player
    prefix = "▶" if is_active else " "
    formatted = " | ".join(_format_skill_status(status, is_active) for status in statuses)
    return f"{prefix} {game.player_label(player)}：{formatted}"


def _format_skill_status(status: SkillStatus, is_active_player: bool) -> str:
    hotkey = SKILL_HOTKEYS.get(status.name, "?")
    ready = status.cooldown_remaining == 0
    readiness = "就绪" if ready else f"冷却{status.cooldown_remaining}"
    emphasis = "*" if ready and is_active_player else ""
    style: List[str] = []
    if is_active_player:
        style.append(BOLD)
    style.append(FG_GREEN if ready else FG_RED)
    return _color(f"[{hotkey}] {status.name}{emphasis} {readiness}", *style)


def _render_action_log_panel(game: Game, height: int) -> List[str]:
    lines: List[str] = []
    lines.append(_color("最近行动", BOLD, FG_MAGENTA))
    if game.action_log:
        for entry in reversed(game.action_log):
            lines.append(_color(entry, FG_BLUE))
    else:
        lines.append(_color("—", FG_WHITE, DIM))

    if len(lines) < height:
        lines.extend([""] * (height - len(lines)))
    return lines[:height]


def _render_controls_line() -> str:
    return _color(
        "操作：W/A/S/D 移动 | 空格 落子 | 1-4 使用技能 | R 重开 | Q 退出",
        FG_CYAN,
    )


def _render_cell(token: str | None) -> str:
    if token is None or token == EMPTY_CELL:
        return "·"
    if token == BLACK_STONE:
        return "●"
    if token == WHITE_STONE:
        return "○"
    return token


def _render_cursor_cell(token: str | None) -> str:
    if token is None or token == EMPTY_CELL:
        return CURSOR_MARKER
    if token == BLACK_STONE:
        return _color(CURSOR_OCCUPIED_BLACK, FG_CYAN, BOLD)
    if token == WHITE_STONE:
        return _color(CURSOR_OCCUPIED_WHITE, FG_CYAN, BOLD)
    return _color(_render_cell(token), FG_CYAN, BOLD)


def _render_neighbor_cell(token: str | None) -> str:
    if token is None or token != EMPTY_CELL:
        return _render_cell(token)
    return _color(NEIGHBOR_MARKER, FG_BLUE, BOLD)


def _format_cursor(cursor: tuple[int, int]) -> str:
    row, col = cursor
    return f"{COL_LABELS[col]}{row}"


def _color(text: str, *codes: str) -> str:
    if not codes:
        return text
    prefix = "".join(codes)
    return f"{prefix}{text}{RESET}"


def _render_status_box(game: Game, width: int) -> Iterable[str]:
    box_lines = STATUS_BOX.render(game.status_messages, width)
    # Highlight borders for readability
    colored: List[str] = []
    for idx, line in enumerate(box_lines):
        if idx == 0 or idx == len(box_lines) - 1:
            colored.append(_color(line, FG_WHITE, BOLD))
        else:
            colored.append(_color(line, FG_YELLOW))
    return colored


def _combine_with_overlay(base_lines: List[str], overlay_lines: List[str]) -> List[str]:
    combined: List[str] = []
    for idx, base in enumerate(base_lines):
        overlay = overlay_lines[idx] if idx < len(overlay_lines) else ""
        combined.append(_overlay_line(base, overlay))
    return combined


def _overlay_line(base: str, overlay: str) -> str:
    if not overlay.strip():
        return base
    return overlay


def _neighbor_empty_cells(game: Game, cursor: tuple[int, int]) -> Set[tuple[int, int]]:
    neighbors: Set[tuple[int, int]] = set()
    row, col = cursor
    for d_row in (-1, 0, 1):
        for d_col in (-1, 0, 1):
            if d_row == 0 and d_col == 0:
                continue
            target = (row + d_row, col + d_col)
            if not game.board.is_within_bounds(target):
                continue
            if game.board.is_empty(target):
                neighbors.add(target)
    return neighbors
