"""AI opponent orchestration for Gomoku."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Iterable, Optional

from ..board import Coordinate
from ..game import Game, Player
from .personas import AIPersona, SEIZE_AND_MOVE, STONE_STORM
from .search import choose_move


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

        if self._try_use_skill(game):
            return True

        coord = choose_move(game, self.persona.search_depth, rng=self.rng)
        game.set_cursor(coord)
        game.place_at_cursor()
        return True

    # ------------------------------------------------------------------
    # Skill helpers
    # ------------------------------------------------------------------
    def _try_use_skill(self, game: Game) -> bool:
        if self.persona.skill_trigger_chance <= 0:
            return False
        if self.rng.random() >= self.persona.skill_trigger_chance:
            return False

        available = tuple(self._available_skill_names(game))
        if not available:
            return False

        skill_name = self.persona.pick_skill(self.rng, available)
        if skill_name is None:
            return False

        if not self._prepare_skill(skill_name, game):
            return False

        try:
            game.use_skill(skill_name)
            return True
        except ValueError:
            # Fallback to normal move if skill application fails.
            return False

    def _available_skill_names(self, game: Game) -> Iterable[str]:
        cooldowns = game.skill_cooldowns[self.player]
        for name in game.skill_registry:
            if cooldowns.get(name, 0) == 0:
                yield name

    def _prepare_skill(self, skill_name: str, game: Game) -> bool:
        if skill_name == SEIZE_AND_MOVE:
            target = self._find_opponent_stone(game)
            if target is None:
                return False
            game.set_cursor(target)
            return True
        if skill_name == STONE_STORM:
            return bool(list(game.occupied_by_player(self.player.opponent)))
        return True

    def _find_opponent_stone(self, game: Game) -> Optional[Coordinate]:
        opponent_coords = list(game.occupied_by_player(self.player.opponent))
        if not opponent_coords:
            return None
        return self.rng.choice(opponent_coords)


def create_ai_opponent(persona: AIPersona, player: Player, rng: Optional[random.Random] = None) -> AIOpponent:
    """Factory helper that seeds the opponent's RNG consistently."""

    return AIOpponent(persona=persona, player=player, rng=rng or random.Random())
