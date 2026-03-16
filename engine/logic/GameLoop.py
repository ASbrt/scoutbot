import random
from typing import Optional
from engine.controllers.RoundController import RoundController, RoundStage
from engine.controllers.GameController import GameController
from tools.Logging import RoundResult, GameResult


def play_round(bots: list, rng: random.Random, n_players: int, round_num: int, scores_in: list[int],
               start_player: Optional[int] = None, log_turns: bool = True) -> RoundResult:
    """
    Play one full round automatically.
    This wrapper is intended for batch execution only, all players must be bots. Used within play_game()
    """
    controller = RoundController(
        bots=bots,
        rng=rng,
        n_players=n_players,
        round_num=round_num,
        scores_in=scores_in,
        start_player=start_player,
        log_turns=log_turns,
    )
    controller.start_round()

    # Flip phase: resolve all players
    while controller.stage == RoundStage.FLIP:
        if not controller.current_actor_is_bot():
            raise RuntimeError("GameLoops play_round() requires all players to be bots during FLIP stage")
        controller.run_bot_flip_step()

    # Turn phase: resolve all turns
    while controller.stage == RoundStage.TURNS:
        if not controller.current_actor_is_bot():
            raise RuntimeError("GameLoops play_round requires all players to be bots during TURNS stage")
        controller.run_bot_turn()

    if controller.stage != RoundStage.FINISHED:
        raise RuntimeError(f"Round ended in unexpected stage: {controller.stage}")

    return controller.finalize_round()


def play_game(game_id: int, seed: int, bots: list, rng: random.Random, n_players: int,
              log_turns: bool = True) -> GameResult:
    """
    Play one full game automatically.

    This wrapper is intended for batch execution only, all players must be bots.
    """
    controller = GameController(
        bots=bots,
        rng=rng,
        n_players=n_players,
        log_turns=log_turns,
        game_id=game_id,
        seed=seed,
    )

    while not controller.is_finished:
        round_controller = controller.start_next_round()

        # Flip phase
        while round_controller.stage == RoundStage.FLIP:
            if not round_controller.current_actor_is_bot():
                raise RuntimeError("play_game requires all players to be bots during FLIP stage")
            round_controller.run_bot_flip_step()

        # Turn phase
        while round_controller.stage == RoundStage.TURNS:
            if not round_controller.current_actor_is_bot():
                raise RuntimeError("play_game requires all players to be bots during TURNS stage")
            round_controller.run_bot_turn()

        if round_controller.stage != RoundStage.FINISHED:
            raise RuntimeError(f"Round ended in unexpected stage: {round_controller.stage}")

        controller.finalize_current_round()

    return controller.build_result()
