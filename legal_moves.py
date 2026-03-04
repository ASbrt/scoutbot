from GameState import *
from helpers import determine_show_candidates, compute_show_rank

def get_legal_show_candidates(state: GameState) -> list[ShowCandidate]:
    """
    Using a list of ShowCandidates, compares them to the active show on the table.
    Determines the list of all playable ShowCandidates given the current table in GameState.
    Playable ShowCandidates are the ones that beat the Show that is active on the table.
    :param state:
    :return:
    """
    hand = state.hands[state.current_player]
    candidates = determine_show_candidates(hand)

    if state.table is None:
        return candidates

    return [candidate for candidate in candidates if candidate.rank > state.table.rank]

def apply_show_move(state: GameState, candidate: ShowCandidate, advance_turn: bool = True) -> GameState:
    """
    Applies a ShowCandidate to the GameState, removing the cards indicated by the Candidate from the active players hand,
    a new GameState is built with the new Show. Beating an active Show on table yields len(GameState.table.cards) points
    for the active player.

    Use: Always replace current GameState!

    :param state: Current GameState object
    :param candidate: Selected ShowCandidate from active players hand
    :return: New GameState
    """
    active_player = state.current_player
    active_hand = state.hands[active_player]

    start = candidate.start
    end = start + candidate.length

    played_cards = tuple(active_hand[start:end])
    new_hand = active_hand[:start] + active_hand[end:]

    # copy scores before modifying!
    new_scores = list(state.scores)
    if state.table is not None:
        new_scores[active_player] += len(state.table.cards)

    new_show = Show(
        cards=played_cards,
        played_by=active_player,
        kind=candidate.kind,
        rank=candidate.rank
    )

    # copy hands before modifying!
    updated_hands = list(state.hands)
    updated_hands[active_player] = new_hand

    # Advance if flag is not purposefully set to false (-> relevant for Scout&Show Move)
    next_player = (active_player + 1) % len(updated_hands) if advance_turn else active_player

    return GameState(
        hands=updated_hands,
        current_player=next_player,
        table=new_show,
        scores=new_scores,
        scout_and_show_tokens=list(state.scout_and_show_tokens),
        round_num=state.round_num,
        start_player=state.start_player,
        last_show_player=active_player,
    )

def get_legal_scout_candidates(state: GameState) -> list[ScoutCandidate]:
    if state.table is None:
        return []

    hand_len = len(state.hands[state.current_player])
    table_len = len(state.table.cards)

    legal_table_indices = [0]
    if table_len > 1:
        legal_table_indices.append(table_len - 1)

    candidates = []
    for table_index in legal_table_indices:
        for insert_index in range(hand_len + 1):
            for flip in (False, True):
                candidates.append(ScoutCandidate(table_index, insert_index, flip))

    return candidates

def apply_scout_move(state: GameState, candidate: ScoutCandidate, advance_turn: bool = True) -> GameState:
    """
    Applies a ScoutCandidate to GameState:
    1. Takes the chosen candidate from the tables active show
    2. Flips the Card object if necessary
    3. inserts it into the active players hand at insert_index
    4. Updates the table show (table can become empty -> set to None)
    5. advances to next player
    """
    active_player = state.current_player
    active_hand = state.hands[active_player]

    table_cards = list(state.table.cards)
    taken_card = table_cards.pop(candidate.table_index)

    if candidate.flip:
        taken_card = taken_card.flip_card()

    insert_index = candidate.hand_insert_index
    new_hand = active_hand[:insert_index] + [taken_card] + active_hand[insert_index:]

    # rebuild show on table
    new_table = None
    if len(table_cards) > 0:
        active_values = [card.active for card in table_cards]
        rank = compute_show_rank(active_values)
        kind = 'set' if rank[1] == 1 else "run"
        new_table = Show(cards=tuple(table_cards), played_by=state.table.played_by, kind=kind, rank=rank)

    updated_hands = list(state.hands)
    updated_hands[active_player] = new_hand

    # Award a point to the player who played the show originally
    new_scores = list(state.scores)
    show_owner = state.table.played_by
    new_scores[show_owner] += 1

    # Advance turn if not purposefully set to false (-> relevant for Scout&Show Move)
    next_player = (active_player + 1) % len(updated_hands) if advance_turn else active_player

    return GameState(
        hands=updated_hands,
        current_player=next_player,
        table=new_table,
        scores=new_scores,
        scout_and_show_tokens=list(state.scout_and_show_tokens),
        round_num=state.round_num,
        start_player=state.start_player,
        last_show_player=state.last_show_player,
    )

def get_legal_scout_and_show_candidates(state: GameState) -> list[ScoutAndShowCandidate]:
    active_player = state.current_player
    if not state.scout_and_show_tokens[active_player]:
        return []

    possible_moves = []
    for scout_cand in get_legal_scout_candidates(state):
        scout_state = apply_scout_move(state, scout_cand, advance_turn=False)
        for show_cand in get_legal_show_candidates(scout_state):
            possible_moves.append(ScoutAndShowCandidate(scout_cand, show_cand))

    return possible_moves

def apply_scout_and_show_move(state: GameState, candidate: ScoutAndShowCandidate) -> GameState:
    active_player = state.current_player
    if not state.scout_and_show_tokens[active_player]:
        raise ValueError('Scout&Show already used in this round')

    #Combination of the 2 base moves, building a new state
    step_1 = apply_scout_move(state, candidate.scout, advance_turn=False)
    step_2 = apply_show_move(step_1, candidate.show, advance_turn=False)

    # Consume the Scout&Show token
    tokens = list(step_2.scout_and_show_tokens)
    tokens[active_player] = False

    next_player = (active_player + 1) % len(step_2.hands)
    return GameState(
        hands=step_2.hands,
        current_player=next_player,
        table=step_2.table,
        scores=step_2.scores,
        scout_and_show_tokens=tokens,
        round_num=step_2.round_num,
        start_player=step_2.start_player,
        last_show_player=step_2.last_show_player
    )

def get_all_legal_moves(state: GameState) -> list[Move]:
    """
    Top level api-call for returning all possible moves
    :param state:
    :return:
    """
    moves = []

    for sh_candidate in get_legal_show_candidates(state):
        moves.append(ShowMove(sh_candidate))
    for sc_candidate in get_legal_scout_candidates(state):
        moves.append(ScoutMove(sc_candidate))
    for scsh_candidate in get_legal_scout_and_show_candidates(state):
        moves.append(ScoutAndShowMove(scsh_candidate))

    return moves

def apply_move(state: GameState, move: Move) -> GameState:
    """
    Top level api-call for applying the correct state transition based on the move type passed in
    :param state:
    :param move:
    :return:
    """
    if isinstance(move, ShowMove):
        return apply_show_move(state, move.candidate, advance_turn=True)

    if isinstance(move, ScoutMove):
        return apply_scout_move(state, move.candidate, advance_turn=True)

    if isinstance(move, ScoutAndShowMove):
        return apply_scout_and_show_move(state, move.candidate)

    raise TypeError(f'Unknown move type: {type(move)}')