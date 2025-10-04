"""AI opponent orchestration for Gomoku."""

from __future__ import annotations

import copy
import random
from dataclasses import dataclass
from typing import Optional

from ..board import Coordinate
from ..game import Game, Player
from .personas import AIPersona, SEIZE_AND_MOVE, STONE_STORM
from .search import SearchAction, choose_action, choose_move


@dataclass
class AIOpponent:
    """Automates turns for a given persona and player color."""

    persona: AIPersona
    player: Player
    rng: random.Random

    def take_turn(self, game: Game) -> bool:
        """Execute the AI's turn if it is the configured player's move."""

        if game.current_player is not self.player:
            return False

        action = choose_action(game, self.persona.search_depth, rng=self.rng)
        if action.skill is not None:
            if self._execute_skill(action, game):
                return True
            coord = self._fallback_move(game)
            if coord is None:
                return False
            game.set_cursor(coord)
            game.place_at_cursor()
            return True

        coord = action.move
        if coord is None:
            coord = self._fallback_move(game)
            if coord is None:
                return False
        game.set_cursor(coord)
        game.place_at_cursor()
        return True

    def _execute_skill(self, action: SearchAction, game: Game) -> bool:
        skill_name = action.skill
        assert skill_name is not None  # for type checkers

        if skill_name == STONE_STORM and action.skill_target is not None:
            game.set_cursor(action.skill_target)
        elif skill_name == SEIZE_AND_MOVE:
            cursor_coord = action.skill_target or self._fallback_seize_target(game)
            if cursor_coord is None:
                return False
            game.set_cursor(cursor_coord)

        try:
            game.use_skill(skill_name)
            return True
        except ValueError:
            return False

    def _fallback_seize_target(self, game: Game) -> Optional[Coordinate]:
        opponent_coords = list(game.occupied_by_player(self.player.opponent))
        if not opponent_coords:
            return None
        return self.rng.choice(opponent_coords)

    def _fallback_move(self, game: Game) -> Optional[Coordinate]:
        snapshot = copy.deepcopy(game)
        cooldowns = snapshot.skill_cooldowns[snapshot.current_player]
        for name in cooldowns:
            cooldowns[name] = max(cooldowns[name], 1)
        try:
            return choose_move(snapshot, self.persona.search_depth, rng=self.rng)
        except ValueError:
            return None


def create_ai_opponent(persona: AIPersona, player: Player, rng: Optional[random.Random] = None) -> AIOpponent:
    """Factory helper that seeds the opponent's RNG consistently."""

    return AIOpponent(persona=persona, player=player, rng=rng or random.Random())
