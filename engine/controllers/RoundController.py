import random
from enum import Enum, auto
from typing import Optional, List
from engine.state.CardCore import build_deck, deal_hands, Card
from engine.state.GameState import GameState, Move
from engine.logic.legal_moves import get_all_legal_moves, apply_move
from engine.logic.helpers import flip_entire_hand, any_empty_hand, unbeaten_show_cycle,apply_end_of_round_penalties
from tools.Logging import TurnRecord, RoundResult


class RoundStage(Enum):
    """
    An enum for state tracking. Helps with transitioning between different phases of a round. The previous GameLoop approach
    was not suited for the more granular control needed for human interaction. This m
    """
    CREATED = auto()
    FLIP = auto()
    TURNS = auto()
    FINISHED = auto()


class RoundController:
    """
    Controls the execution of a single round of Scout. This controller is UI-agnostic:
    - it knows and respects round stages (flip / turn / finished),
    - accepts complete move objects
    - does NOT know anything about cursor positions, selected indices, etc.
    """

    def __init__(self,
        bots: list,
        rng: random.Random,
        n_players: int,
        round_num: int,
        scores_in: List[int],
        start_player: Optional[int] = None,
        log_turns: bool = True,
    ):
        if len(bots) != n_players:
            raise ValueError(f"Need {n_players} players, got {len(bots)} in bot list")

        # Round setup parameters
        self.bots = bots
        self.rng = rng
        self.n_players = n_players
        self.round_num = round_num
        self.scores_in = list(scores_in)
        self.start_player = start_player
        self.log_turns = log_turns

        # Lifecycle init
        self.stage = RoundStage.CREATED

        # Flip-phase
        self.pending_hands: Optional[List[List[Card]]] = None
        self.flip_player_index: int = 0

        # Turns-phase
        self.state: Optional[GameState] = None
        self.legal_moves: List[Move] = []
        self.turn_index: int = 0
        self.turn_log: List[TurnRecord] = []
        self.ended_by_unbeaten_cycle: bool = False

    # 2 computed state helpers, implemented as properties so it's possible to treat them like attributes
    @property
    def is_started(self) -> bool:
        return self.stage != RoundStage.CREATED

    @property
    def is_finished(self) -> bool:
        return self.stage == RoundStage.FINISHED


    def start_round(self) -> None:
        """
        Handles Round setup, building a deck and distributing cards. Initializes tracking
        variables used throughout the round and transitions to FlIP decision phase afterwards
        """
        if self.stage != RoundStage.CREATED:
            raise RuntimeError("Round already started")

        deck = build_deck(self.rng, n_players=self.n_players)
        self.pending_hands = deal_hands(deck, n_players=self.n_players)

        if self.start_player is None:
            self.start_player = self.rng.randrange(self.n_players)

        self.flip_player_index = 0
        self.turn_index = 0
        self.turn_log = []
        self.ended_by_unbeaten_cycle = False
        self.state = None
        self.legal_moves = []

        self.stage = RoundStage.FLIP

    def current_actor_is_bot(self) -> bool:
        """
        Helper method: Returns a boolean to indicate whether the player that currently needs to act is a bot.
        """
        if self.stage == RoundStage.FLIP:
            return self.bots[self.flip_player_index] is not None

        if self.stage == RoundStage.TURNS:
            if self.state is None:
                raise RuntimeError("TURN stage without GameState")
            return self.bots[self.state.current_player] is not None

        return False

    def current_flip_player(self) -> int:
        """
        Helper method: Returns player index of current flip decider
        """
        if self.stage != RoundStage.FLIP:
            raise RuntimeError("Not in flip phase")
        return self.flip_player_index

    def current_turn_player(self) -> int:
        """
        Helper method: Returns player index of the active player
        """
        if self.stage != RoundStage.TURNS or self.state is None:
            raise RuntimeError("Not in turn phase")
        return self.state.current_player

    # Flip phase methods:

    def get_flip_hand(self) -> List[Card]:
        """
        Returns the current player's pending hand during FLIP stage. Useful for showing the FlipScreen in the TUI.
        """
        if self.stage != RoundStage.FLIP or self.pending_hands is None:
            raise RuntimeError("Not in flip phase")
        return self.pending_hands[self.flip_player_index]

    def submit_flip_decision(self, flipped: bool) -> None:
        """
        Takes in and submits one player's flip decision. Once the last player has decided, the controller
        transitions to TURNS.
        """
        if self.stage != RoundStage.FLIP:
            raise RuntimeError("submit_flip_decision is only valid in FLIP stage")
        if self.pending_hands is None:
            raise RuntimeError("Flip phase has no pending hands")

        player = self.flip_player_index

        if flipped:
            self.pending_hands[player] = flip_entire_hand(self.pending_hands[player])

        self.flip_player_index += 1

        if self.flip_player_index >= self.n_players:
            self._finish_flip_phase()

    def run_bot_flip_step(self) -> bool:
        """
        Resolve exactly one bot flip decision. Returns the bot's flip decision.
        """
        if self.stage != RoundStage.FLIP:
            raise RuntimeError("run_bot_flip_step only valid in FLIP stage")
        if self.pending_hands is None:
            raise RuntimeError("Flip phase has no pending hands")

        player = self.flip_player_index
        bot = self.bots[player]
        if bot is None:
            raise RuntimeError("Current flip actor is human, cannot auto-run bot flip")

        flipped = bot.choose_flip(self.pending_hands[player], player, self.rng)

        self.submit_flip_decision(flipped)
        return flipped

    def run_all_bot_flips_until_human_or_turn(self) -> None:
        """
        Convenience method, keeps resolving bot flips until either
        - a human flip decision is needed, or
        - flip phase is done and we enter TURNS
        """
        while self.stage == RoundStage.FLIP and self.current_actor_is_bot():
            self.run_bot_flip_step()

    def _finish_flip_phase(self) -> None:
        """
        Private method! Constructs initial GameState object and handles transition from FLIP -> TURNS
        """
        if self.pending_hands is None:
            raise RuntimeError("Cannot finish flip phase without pending hands")
        if self.start_player is None:
            raise RuntimeError("start_player must be set before entering TURNS")

        self.state = GameState(
            hands=self.pending_hands,
            current_player=self.start_player,
            table=None,
            scores=list(self.scores_in),
            scout_and_show_tokens=[True] * self.n_players,
            round_num=self.round_num,
            start_player=self.start_player,
            last_show_player=None,
        )

        self.pending_hands = None
        self.flip_player_index = 0
        self.stage = RoundStage.TURNS
        self._refresh_legal_moves()

    # Turn phase methods
    def _refresh_legal_moves(self) -> None:
        """
        Private method! Loads legal moves
        """
        if self.stage != RoundStage.TURNS or self.state is None:
            self.legal_moves = []
            return

        self.legal_moves = get_all_legal_moves(self.state)

    def _check_round_end(self) -> bool:
        """
        Private method! Returns True if the round is over after the current state. Rounds end by
        - a player emptying their hand by playing a show, or
        - a player playing a show no other player can beat
        """
        if self.state is None:
            raise RuntimeError("No GameState to check")

        if any_empty_hand(self.state):
            return True

        if unbeaten_show_cycle(self.state):
            self.ended_by_unbeaten_cycle = True
            return True

        return False

    def apply_selected_move(self, move: Move) -> None:
        """
        Apply one complete move in TURNS stage. Used for both human-submitted moves and bot-selected moves.
        """
        if self.stage != RoundStage.TURNS:
            raise RuntimeError("apply_selected_move only valid in TURNS stage")
        if self.state is None:
            raise RuntimeError("TURNS stage without GameState")

        state_before = self.state
        player = state_before.current_player

        if self.log_turns:
            scores_before = list(state_before.scores)
            hand_sizes_before = [len(h) for h in state_before.hands]
            table_rank_before = state_before.table.rank if state_before.table else None

        state_after = apply_move(state_before, move)

        if self.log_turns:
            self.turn_log.append(
                TurnRecord(
                    round_num=self.round_num,
                    turn_index=self.turn_index,
                    player=player,
                    move=move,
                    scores_before=scores_before,
                    scores_after=list(state_after.scores),
                    hand_sizes_before=hand_sizes_before,
                    hand_sizes_after=[len(hand) for hand in state_after.hands],
                    table_rank_before=table_rank_before,
                    table_rank_after=state_after.table.rank if state_after.table else None,
                )
            )

        self.state = state_after
        self.turn_index += 1

        if self._check_round_end():
            self.stage = RoundStage.FINISHED
            self.legal_moves = []
        else:
            self._refresh_legal_moves()

    def run_bot_turn(self) -> Move:
        """
        Resolve exactly one bot turn. Returns the chosen move.
        """
        if self.stage != RoundStage.TURNS:
            raise RuntimeError("run_bot_turn only valid in TURN stage")
        if self.state is None:
            raise RuntimeError("TURN stage without GameState")

        player = self.state.current_player
        bot = self.bots[player]
        if bot is None:
            raise RuntimeError("Current turn actor is human, cannot auto-run bot turn")

        move = bot.select_move(self.state, self.legal_moves, self.rng)
        self.apply_selected_move(move)
        return move

    def run_all_bot_turns_until_human_or_finished(self) -> None:
        """
        Convenience method: keeps resolving bot turns until either
        - a human move is needed, or
        - the round finishes.
        """
        while self.stage == RoundStage.TURNS and self.current_actor_is_bot():
            self.run_bot_turn()

    # Finalization/Round clean up

    def finalize_round(self) -> RoundResult:
        """
        Builds and returns the RoundResult
        """
        if self.stage != RoundStage.FINISHED:
            raise RuntimeError("finalize_round only valid in FINISHED stage")
        if self.state is None:
            raise RuntimeError("FINISHED stage without GameState")

        scores_out = apply_end_of_round_penalties(
            self.state,
            unbeaten_show_cycle=self.ended_by_unbeaten_cycle,
        )

        return RoundResult(
            round_num=self.round_num,
            start_player=self.start_player,
            end_reason="unbeaten_show_cycle" if self.ended_by_unbeaten_cycle else "empty_hand",
            scores_in=list(self.scores_in),
            scores_out=list(scores_out),
            turn_log=list(self.turn_log),
        )