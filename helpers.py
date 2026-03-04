from simulation_core import Card
from GameState import ShowCandidate, GameState

def get_active_values(hand: list[Card]) -> list[int]:
    """
    For a hand (list of card objects) return a list of active values (based on card orientation)
    :param hand: a list of card objects
    :return: a list of active values
    """
    return [card.active for card in hand]

def flip_entire_hand(hand: list[Card]) -> list[Card]:
    """
    At the start of a round players may decide to flip around all the cards in their hand at once
    :param hand: a list of card objects
    :return: a list of card objects with their orientation flipped
    """
    return [card.flip_card() for card in hand]

def is_set(values: list[int]) -> bool:
    """
    Determines if a block of values is a set (multiple of the same number)
    :param values: list of ints
    :return: Boolean
    """
    return len(values) > 1 and all(v == values[0] for v in values)

def is_run(values: list[int]) -> bool:
    """
    Determines if a block of values is a run (numbers in ascending/descending order). Blocks of length 1 are treated as valid runs
    :param values: list of ints
    :return: Boolean
    """
    if len(values) == 1:
        return True

    increasing = all(values[i+1] == values[i] + 1 for i in range(len(values) - 1))
    decreasing = all(values[i+1] == values[i] - 1 for i in range(len(values) - 1))

    return increasing or decreasing

def compute_show_rank(values: list[int]) -> tuple[int, int, int] | None:
    """
    Returns (length, kind_rank, value_rank). Rank determines the power level of a given show, and is
    used in determining if a move is legal to play.
    kind_rank: 1=set, 0=run, None if unplayable
    value_rank: max(values)

    """
    if is_set(values):
        kind_rank = 1
    elif is_run(values):
        kind_rank = 0
    else:
        return None

    return (len(values), kind_rank, max(values))


def determine_show_candidates(hand: list[Card]) -> list[ShowCandidate]:
    """
    Determines all playable shows from a given hand by evaluating all possible blocks (ranges of cards in hand).
    :param hand: list of card objects
    :return: list of ShowCandidates
    """
    candidates: list[ShowCandidate] = []
    n = len(hand)

    for start in range(n):
        for end in range(start + 1, n + 1):
            block = hand[start:end]
            values = get_active_values(block)

            rank = compute_show_rank(values)
            if rank is None:
                continue

            kind = "set" if rank[1] == 1 else "run"

            candidates.append(
                ShowCandidate(
                    start=start,
                    length=end - start,
                    kind=kind,
                    rank=rank,
                    values=values,
                )
            )

    return candidates

def any_empty_hand(state: GameState) -> bool:
    """
    Round termination helper for determining if any player emptied their hand
    :param state:
    """
    return any(len(hand) == 0 for hand in state.hands)

def unbeaten_show_cycle(state: GameState) -> bool:
    """
    Round termination helper for evaluating the second round end condition, which is a player putting out a Show Move
    no other player can beat, so they're all forced to scout
    :param state:
    """
    return (state.table is not None and state.last_show_player is not None and state.current_player == state.last_show_player)

def apply_end_of_round_penalties(state: GameState, unbeaten_show_cycle: bool = False) -> list[int]:
    """
    The engine already awards points for beating shows and scouting moves. At the end of a round any remaining cards in
    hand are treated as negative points. A player who played an unbeaten show is exempt from point deduction due to
    remaining cards in hand.
    :param state: Ending GameState
    :param unbeaten_show_cycle: True if a player played an unbeaten show
    :return: Updates Scores
    """
    scores = list(state.scores)
    exempt_player = state.last_show_player if unbeaten_show_cycle else None

    for player, hand in enumerate(state.hands):
        if exempt_player is not None and player == exempt_player:
            continue
        scores[player] -= len(hand)

    return scores