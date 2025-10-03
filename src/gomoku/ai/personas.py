"""Persona definitions for the Gomoku AI opponent."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, Iterable, Mapping, Optional

from ..skills import ALL_SKILLS

# Skill names used by personas
STONE_STORM = "飞沙走石"
STILL_WATERS = "静如止水"
SEIZE_AND_MOVE = "擒擒拿拿"
MIGHTY_CLEARING = "力拔山兮"


@dataclass(frozen=True)
class AIPersona:
    """Configuration bundle describing an AI opponent persona."""

    key: str
    display_name: str
    level: int
    search_depth: int
    skill_weights: Mapping[str, float]
    skill_trigger_chance: float = 1 / 3
    no_skill_weight: float = 0.0
    description: Optional[str] = None

    def pick_skill(self, rng: random.Random, available_skills: Iterable[str]) -> Optional[str]:
        """Sample a skill name based on the persona's weights.

        Returns ``None`` when the persona elects not to use a skill or no
        eligible skills remain.
        """

        weighted_choices: list[tuple[Optional[str], float]] = []
        total_weight = 0.0
        skill_set = set(available_skills)
        for skill_name, weight in self.skill_weights.items():
            if weight <= 0.0:
                continue
            if skill_name not in skill_set:
                continue
            weighted_choices.append((skill_name, float(weight)))
            total_weight += float(weight)

        if self.no_skill_weight > 0:
            weighted_choices.append((None, float(self.no_skill_weight)))
            total_weight += float(self.no_skill_weight)

        if not weighted_choices or total_weight <= 0:
            return None

        threshold = rng.random() * total_weight
        for skill_name, weight in weighted_choices:
            if threshold < weight:
                return skill_name
            threshold -= weight
        return weighted_choices[-1][0]


@dataclass(frozen=True)
class PersonaRegistry:
    """Collection of persona definitions with helper lookups."""

    personas: tuple[AIPersona, ...] = field(default_factory=tuple)
    _by_key: Dict[str, AIPersona] = field(init=False, repr=False)
    _by_level: Dict[int, AIPersona] = field(init=False, repr=False)

    def __post_init__(self) -> None:  # pragma: no cover - simple mapping setup
        object.__setattr__(self, "_by_key", {persona.key: persona for persona in self.personas})
        object.__setattr__(self, "_by_level", {persona.level: persona for persona in self.personas})

    def get(self, identifier: str | int) -> AIPersona:
        if isinstance(identifier, int):
            persona = self._by_level.get(identifier)
        else:
            persona = self._by_key.get(identifier)
        if persona is None:
            raise KeyError(f"未找到编号为 {identifier} 的对手信息")
        return persona

    def __iter__(self):  # pragma: no cover - trivial delegation
        return iter(self.personas)

    def keys(self):  # pragma: no cover
        return self._by_key.keys()

    def values(self):  # pragma: no cover
        return self.personas


_PERSONAS: tuple[AIPersona, ...] = (
    AIPersona(
        key="ziqi",
        display_name="子棋",
        level=1,
        search_depth=1,
        skill_weights={STONE_STORM: 0.4, STILL_WATERS: 0.4, SEIZE_AND_MOVE: 0.1},
        no_skill_weight=0.1,
        description="新入门的小棋友，偶尔会忘记释放技能。",
    ),
    AIPersona(
        key="zhangcheng",
        display_name="张呈",
        level=2,
        search_depth=2,
        skill_weights={STONE_STORM: 0.4, STILL_WATERS: 0.1, SEIZE_AND_MOVE: 0.55, MIGHTY_CLEARING: 0.05},
        description="课堂上的捣蛋王，最爱搬运和拆家。",
    ),
    AIPersona(
        key="coach-wang",
        display_name="王教练",
        level=3,
        search_depth=3,
        skill_weights={STONE_STORM: 0.4, SEIZE_AND_MOVE: 0.6},
        description="稳重又老辣，总想着擒拿对手的痛点。",
    ),
    AIPersona(
        key="jinengwu",
        display_name="技能五",
        level=4,
        search_depth=4,
        skill_weights={STONE_STORM: 0.2, SEIZE_AND_MOVE: 0.6, MIGHTY_CLEARING: 0.2},
        description="传说中的终极老师，技能运用炉火纯青。",
    ),
)

PERSONAS = PersonaRegistry(_PERSONAS)


def get_persona(identifier: str | int) -> AIPersona:
    """Convenience wrapper returning the persona by key or level."""

    return PERSONAS.get(identifier)


def available_skill_names() -> tuple[str, ...]:
    """Return the canonical tuple of skill names used by personas."""

    return tuple(ALL_SKILLS.keys())
