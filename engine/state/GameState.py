from dataclasses import dataclass
from engine.state.CardCore import Card
from typing import Optional

"""
This file holds MoveCandidates and Moves that are needed for the files in logic to determine legal moves and apply them
back to state. This file also holds the GameState object which serves as the source of truth for each round of a game. 
All classes are frozen as to prevent mutations in place.
"""

@dataclass(frozen=True)
class ShowCandidate:
    start: int
    length: int
    kind: str    # "run" (e.g. 1, 2, 3) or "set" (e.g. 5, 5)
    rank: tuple[int, int, int] # Stores in order: length, kind (set 1, run 0), max(value)
    values: list[int]

@dataclass(frozen=True)
class Show:
    cards: tuple[Card, ...]
    kind: str
    rank: tuple[int, int, int]
    played_by: int

@dataclass(frozen=True)
class ScoutCandidate:
    table_index: int
    hand_insert_index: int
    flip: bool

@dataclass(frozen=True)
class ScoutAndShowCandidate:
    scout: ScoutCandidate
    show: ShowCandidate

@dataclass(frozen=True)
class ShowMove:
    candidate: ShowCandidate

@dataclass(frozen=True)
class ScoutMove:
    candidate: ScoutCandidate

@dataclass(frozen=True)
class ScoutAndShowMove:
    candidate: ScoutAndShowCandidate

Move = ShowMove | ScoutMove | ScoutAndShowMove

@dataclass(frozen=True)
class GameState:
    """
    Holds global game state. Central source of truth for every game.
    """
    hands: list[list[Card]]
    current_player: int
    table: Optional[Show]
    scores: list[int]
    scout_and_show_tokens: list[bool]
    round_num: int = 1
    start_player: int = 0
    last_show_player: Optional[int] = None
