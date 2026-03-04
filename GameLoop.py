import random
from simulation_core import build_deck, deal_hands
from legal_moves import get_all_legal_moves, apply_move
from helpers import flip_entire_hand, any_empty_hand, unbeaten_show_cycle, apply_end_of_round_penalties
from Logging import *



def play_round(bots: list, rng: random.Random, n_players: int, round_num: int, scores_in: list[int],
    start_player: Optional[int] = None, log_turns: bool = True, verbose: bool = False) -> RoundResult:
    """
    Plays one round: deal -> flip phase -> turn loop -> end-of-round penalties.
    """
    if len(bots) != n_players:
        raise ValueError(f"Need {n_players} bots, got {len(bots)}")

    # Game setup
    deck = build_deck(rng, n_players=n_players)
    hands = deal_hands(deck, n_players=n_players)

    # flip phase (once per player)
    for player in range(n_players):
        choose_flip = getattr(bots[player], "choose_flip", None)
        if callable(choose_flip) and choose_flip(hands[player], player, rng):
            hands[player] = flip_entire_hand(hands[player])

    if start_player is None:
        start_player = rng.randrange(n_players)

    state = GameState(
        hands=hands,
        current_player=start_player,
        table=None,
        scores=list(scores_in),
        scout_and_show_tokens=[True] * n_players,
        round_num=round_num,
        start_player=start_player,
        last_show_player=None,
    )

    # Turn loop
    turn_log: list[TurnRecord] = []
    turn_index = 0

    ended_by_unbeaten_cycle = False

    # Condition A (empty hand) ends the round
    while not any_empty_hand(state):
        # Condition B: unbeaten show cycle ends the round
        if unbeaten_show_cycle(state):
            ended_by_unbeaten_cycle = True
            break

        moves = get_all_legal_moves(state)
        if not moves:
            raise RuntimeError("No legal moves available")

        player = state.current_player
        chosen: Move = bots[player].select_move(state, moves, rng)

        if log_turns:
            scores_before = list(state.scores)
            hand_sizes_before = [len(h) for h in state.hands]
            table_rank_before = state.table.rank if state.table else None

        state2 = apply_move(state, chosen)
        if verbose:
            print_turn(
                round_num=round_num,
                turn_index=turn_index,
                player=player,
                state_before=state,
                move=chosen,
                state_after=state2,
                show_active_hand=True
            )

        if log_turns:
            turn_log.append(
                TurnRecord(
                    round_num=round_num,
                    turn_index=turn_index,
                    player=player,
                    move=chosen,
                    scores_before=scores_before,
                    scores_after=list(state2.scores),
                    hand_sizes_before=hand_sizes_before,
                    hand_sizes_after=[len(hand) for hand in state2.hands],
                    table_rank_before=table_rank_before,
                    table_rank_after=state2.table.rank if state2.table else None,
                )
            )

        state = state2
        turn_index += 1

    scores_out = apply_end_of_round_penalties(state, unbeaten_show_cycle=ended_by_unbeaten_cycle)

    return RoundResult(
        round_num=round_num,
        start_player=start_player,
        end_reason="unbeaten_show_cycle" if ended_by_unbeaten_cycle else "empty_hand",
        scores_in=list(scores_in),
        scores_out=list(scores_out),
        turn_log=turn_log,
    )


def play_game(bots: list, rng: random.Random, n_players: int, log_turns: bool = True, verbose: bool = True) -> GameResult:
    """
    Plays multiple rounds and returns full game result.
    """
    if len(bots) != n_players:
        raise ValueError(f"Need{n_players} bots, got {len(bots)}")

    scores = [0] * n_players
    rounds: list[RoundResult] = []

    start_player = None

    for round in range(1, n_players + 1):
        round_result = play_round(
            bots=bots,
            rng=rng,
            n_players=n_players,
            round_num=round,
            scores_in=scores,
            start_player=start_player,
            log_turns=log_turns,
            verbose=verbose
        )
        rounds.append(round_result)
        scores = round_result.scores_out

        # Rotate start player
        if start_player is None:
            start_player = round_result.start_player
        start_player = (start_player + 1) % n_players

    return GameResult(
        n_players=n_players,
        n_rounds=n_players,
        scores_final=list(scores),
        rounds=rounds,
    )