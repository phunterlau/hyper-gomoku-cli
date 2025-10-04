"""Command-line entry point for the Gomoku TUI game."""

from __future__ import annotations

import time
from typing import Optional

from .ai import PERSONAS, AIPersona, AIOpponent, create_ai_opponent
from .controller import Command, Controller
from .game import Game, Player
from .skills import SKILL_HOTKEYS
from .ui import input as input_mod
from .ui.renderer import render


def main() -> None:  # pragma: no cover - interactive loop
    """Launch the interactive Gomoku game."""

    persona = _prompt_persona_selection()
    human_player = _prompt_player_color()
    ai_player = human_player.opponent

    game = Game.new()
    game.set_player_alias(human_player, "你")
    game.set_player_alias(ai_player, persona.display_name)

    controller = Controller(game)
    ai_opponent = create_ai_opponent(persona, ai_player, rng=game.rng)

    _run_ai_turns(game, ai_opponent)

    while True:
        print("\033[H\033[J", end="")  # Clear terminal
        print(render(game))
        if game.overlay_lines:
            try:
                input_mod.get_key()
            except NotImplementedError:
                game.clear_overlay()
                continue
            game.clear_overlay()
            continue
        try:
            key = input_mod.get_key()
        except NotImplementedError:
            print("键盘输入尚未实现，程序结束。")
            return

        command = _map_key_to_command(key, controller)
        if command == "quit":
            return
        if command:
            try:
                controller.handle_input(command)
            except ValueError as exc:
                controller.game.info_message = str(exc)
            else:
                _run_ai_turns(game, ai_opponent)
        time.sleep(0.01)


def _map_key_to_command(key: str | None, controller: Controller) -> str | None:
    mapping = {
        "w": Command.MOVE_UP,
        "s": Command.MOVE_DOWN,
        "a": Command.MOVE_LEFT,
        "d": Command.MOVE_RIGHT,
        " ": Command.PLACE,
        "r": Command.RESET,
        "q": "quit",
        "6": Command.SECRET_REPORT,
    }
    if key:
        for name, hotkey in SKILL_HOTKEYS.items():
            if key.lower() == hotkey.lower() and name in controller.game.skill_registry:
                return f"{Command.SKILL_PREFIX}{name}"
    return mapping.get(key)


def _prompt_persona_selection() -> AIPersona:
    print("请选择你的对手：")
    persona_list = list(PERSONAS.values())
    for persona in persona_list:
        print(
            f"  {persona.level}. {persona.display_name}"
            f"（Lv{persona.level}，搜索深度 {persona.search_depth}）"
        )

    while True:
        try:
            choice = input("输入编号或名称 [1]: ").strip()
        except EOFError:  # pragma: no cover - non-interactive fallback
            choice = ""
        identifier: int | str
        if not choice:
            identifier = 1
        elif choice.isdigit():
            identifier = int(choice)
        else:
            identifier = choice
        try:
            return PERSONAS.get(identifier)
        except KeyError:
            print("未识别的对手，请重新输入。")


def _prompt_player_color() -> Player:
    prompt = "选择先后手 ([B] 黑棋 / [W] 白棋，默认黑棋): "
    while True:
        try:
            choice = input(prompt).strip().lower()
        except EOFError:  # pragma: no cover - non-interactive fallback
            choice = ""
        if choice in ("", "b", "black", "1", "黑", "先"):
            return Player.BLACK
        if choice in ("w", "white", "2", "白", "后"):
            return Player.WHITE
        print("输入无效，请输入 B 或 W。")


def _run_ai_turns(game: Game, opponent: Optional[AIOpponent]) -> None:
    if opponent is None:
        return
    while not game.is_finished and game.current_player is opponent.player:
        acted = opponent.take_turn(game)
        if not acted:
            break


if __name__ == "__main__":  # pragma: no cover
    main()
