import random
from typing import Optional, List
from engine.controllers.RoundController import RoundController
from tools.Logging import GameResult, RoundResult
from tools.serialization import serialize_seat_types


class GameController:
    """
    Controls a full game of Scout across multiple rounds.

    Responsibilities:
    - track game scores
    - create and manage RoundControllers
    - rotate start player between rounds
    - collect round results
    - build final GameResult
    """

    def __init__(self, game_id: int, seed: int, bots: list, rng: random.Random, n_players: int,
                 log_turns: bool = True, verbose: bool = False):
        if len(bots) != n_players:
            raise ValueError(f"Need {n_players} players, got {len(bots)} in bot list")

        self.bots = bots
        self.rng = rng
        self.n_players = n_players
        self.log_turns = log_turns
        self.game_id = game_id
        self.seed = seed

        self.scores: List[int] = [0] * n_players
        self.round_results: List[RoundResult] = []

        self.round_number: int = 1
        self.start_player: Optional[int] = None

        self.current_round: Optional[RoundController] = None
        self.verbose = verbose

    @property
    def is_finished(self) -> bool:
        return self.round_number > self.n_players

    def start_next_round(self) -> RoundController:
        """
        Create and start the next RoundController
        """
        if self.is_finished:
            raise RuntimeError("Game is already finished")
        if self.current_round is not None:
            raise RuntimeError("Current round must be finalized before starting a new one")

        if self.verbose:
            print(f"Starting new round {self.round_number}...")

        self.current_round = RoundController(
            bots=self.bots,
            rng=self.rng,
            n_players=self.n_players,
            round_num=self.round_number,
            scores_in=self.scores,
            start_player=self.start_player,
            log_turns=self.log_turns,
        )
        self.current_round.start_round()
        return self.current_round

    def finalize_current_round(self) -> RoundResult:
        """
        Finalize the active round, store its result, update scores, rotate start player, and advance the round counter.
        """
        if self.current_round is None:
            raise RuntimeError("No active round to finalize")

        if self.verbose:
            print(f"Finalizing round {self.round_number}")

        result = self.current_round.finalize_round()
        self.round_results.append(result)
        self.scores = list(result.scores_out)

        if self.start_player is None:
            self.start_player = result.start_player
        self.start_player = (self.start_player + 1) % self.n_players

        self.round_number += 1
        self.current_round = None

        return result

    def build_result(self) -> GameResult:
        """
        Build the final GameResult once all rounds are completed.
        """
        if not self.is_finished:
            raise RuntimeError("Game is not finished yet")

        return GameResult(
            game_id=self.game_id,
            seed=self.seed,
            n_players=self.n_players,
            seat_types=serialize_seat_types(self.bots),
            n_rounds=len(self.round_results),
            scores_final=list(self.scores),
            rounds=list(self.round_results),
        )
