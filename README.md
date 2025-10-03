# Gomoku TUI

A terminal-based implementation of 五子棋 (Gomoku) featuring a 15×15 board, keyboard navigation, and three dramatic special skills. The project is currently through Phase 3, delivering core gameplay, TUI integration, and skill mechanics with cooldowns.

## Status

- ✅ Phase 0: Repository scaffolding and tooling ready
- ✅ Phase 1: Board domain logic & win detection complete
- ✅ Phase 2: Turn engine, controller, renderer, and CLI implemented
- ✅ Phase 3: Special skills, cooldown tracking, and testing in place
- ⏳ Phases 4-5: Skill UI refinements, polish, documentation

## Controls

- `W`, `A`, `S`, `D`: Move the cursor across the board
- `Space`: Place the current player's stone
- `1`: Use **飞沙走石** (randomly remove an opponent stone)
- `2`: Use **静如止水** (skip the opponent's next turn)
- `3`: Use **力拔山兮** (clear the entire board)
- `4`: Use **擒擒拿拿** (relocate a highlighted opponent stone to a new empty cell)
- `R`: Reset the match
- `Q`: Quit the CLI session

## Development Setup

```bash
uv sync
```

## Running Tests

```bash
uv run pytest
```

Additional documentation will evolve alongside upcoming phases. For manual test scripts, see `docs/manual-testing.md` (to be expanded in Phase 5).
