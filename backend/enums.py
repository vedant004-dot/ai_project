from enum import Enum


class Difficulty(Enum):
    EASY = 1
    MEDIUM = 2
    HARD = 3


class Algorithm(Enum):
    RANDOM = 1
    MINIMAX = 2
    ALPHA_BETA = 3
    DYNAMIC_HEURISTIC = 4
