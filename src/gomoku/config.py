"""Configuration constants used across the Gomoku project."""

BOARD_SIZE: int = 15
BLACK_STONE: str = "●"
WHITE_STONE: str = "○"
EMPTY_CELL: str = "·"
WIN_SEQUENCE_LENGTH: int = 5

# Default skill cooldowns, measured in completed turns after activation.
SKILL_COOLDOWNS = {
    "飞沙走石": 5,
    "静如止水": 7,
    "力拔山兮": 12,
}
