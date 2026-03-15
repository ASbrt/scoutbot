import random
from pprint import pprint

from engine.state.CardCore import Card, build_deck, deal_hands
from engine.state.GameState import GameState, Show
from engine.logic.helpers import *
from engine.logic.legal_moves import *


"""
A bunch of testing functions. First used for testing legal move application to the table. 

Import and use test_move_generation(seed=5, n_players=3) for a demo of beating logic being applied. It bundles other functions and effectively 
generates a deck of cards, deals them to 3 players, and creates a game state with a mock table with a (5, 5) set. For that 
seed player 2 will have  a playable (8, 8) set that will beat the currently active Show.

This file is sorted into sections, starting with testing for basic Show move, then Scouting, then Scout and Show
"""


def print_hands(hands: list[list[Card]], title: str = "Hands") -> None:
    print(f"\n=== {title} ===")
    for i, hand in enumerate(hands):
        print(f"Player{i}: {get_active_values(hand)}")


def print_table(table: Show | None) -> None:
    print("\n=== Table ===")
    if table is None:
        print("Table is empty")
        return
    print(f"played_by: Player{table.played_by}")
    print(f"kind: {table.kind}")
    print(f"rank: {table.rank}")
    print(f"values: {[card.active for card in table.cards]}")

def make_mock_table_show(played_by: int = 1) -> Show:
    """
    Creates a simple mock table show (not a real Scout card combo).
    """
    cards = (Card(5, 5), Card(5, 5))
    values = [c.active for c in cards]
    rank = compute_show_rank(values)
    assert rank is not None
    kind = "set" if rank[1] == 1 else "run"
    return Show(cards=cards, played_by=played_by, kind=kind, rank=rank)

def test_game_setup_and_flip(seed: int, n_players: int) -> list[list[Card]]:
    """
    Creates a random deck, deals it into n_players hands and flips the entire hand.
    """
    rng = random.Random(seed)
    deck = build_deck(rng, n_players=n_players)
    hands = deal_hands(deck, n_players=n_players)

    print_hands(hands, "Hands after deal (active values)")
    flipped = [flip_entire_hand(h) for h in hands]
    print_hands(flipped, "Hands after flipping entire hand (active values)")
    return flipped


def test_move_generation(seed: int = 3, n_players: int = 3) -> None:
    hands = test_game_setup_and_flip(seed, n_players)

    # Make a mock table show and build state
    table = make_mock_table_show(played_by=1)
    state = GameState(
        hands=hands,
        current_player=2,
        table=table,
        scores=[0] * n_players,
        scout_and_show_tokens=[True] * n_players,
    )

    print_table(state.table)

    legal = get_legal_show_candidates(state)
    print(f"\n=== Legal show candidates for P{state.current_player} ===")
    print(f"count: {len(legal)}")
    pprint(legal[:10])

    if not legal:
        print("\nNo legal show candidates (would need scout/pass logic).")
        return

    chosen = legal[0]
    print("\n=== Applying first legal candidate ===")
    print(chosen)

    state2 = apply_show_move(state, chosen)
    print_table(state2.table)
    print_hands(state2.hands, "Hands after applying show (active values)")
    print(f"\nNext player: Player{state2.current_player}")
    print(f"\nCurrent Scores: {state2.scores}")


"""
Scouting Test Section:
"""

def make_mock_run_show(values: list[int], played_by: int = 1) -> Show:
    cards = tuple(Card(v, v) for v in values)  #
    rank = compute_show_rank(values)
    assert rank is not None
    kind = "set" if rank[1] == 1 else "run"
    return Show(cards=cards, played_by=played_by, kind=kind, rank=rank)

def test_scout_move(seed: int = 5, n_players: int = 3) -> None:
    hands = test_game_setup_and_flip(seed, n_players)

    # table run 3-4-5 owned by player 1
    table = make_mock_run_show([3, 4, 5], played_by=1)

    state = GameState(
        hands=hands,
        current_player=0,
        table=table,
        scores=[0] * n_players,
        scout_and_show_tokens=[True] * n_players,
    )

    print_table(state.table)
    print_hands(state.hands, "Before scout")

    scouts = get_legal_scout_candidates(state)
    print(f"\n=== Scout candidates for P{state.current_player} ===")
    print(f"count: {len(scouts)}")
    pprint(scouts[:8])

    # Pick a deterministic candidate: take left end (index 0), insert at 0, no flip
    chosen = ScoutCandidate(table_index=0, hand_insert_index=0, flip=False)
    print("\n=== Applying scout candidate ===")
    print(chosen)

    state2 = apply_scout_move(state, chosen)

    print_table(state2.table)
    print_hands(state2.hands, "After scout")
    print(f"\nNext player: Player{state2.current_player}")
    print(f"Scores (expect player1 +1): {state2.scores}")

"""
Scout&Show Section:
"""

def test_scout_and_show(seed: int = 5, n_players: int = 3) -> None:
    hands = test_game_setup_and_flip(seed, n_players)

    # table set 5-5 owned by player 1 (your standard)
    table = make_mock_table_show(played_by=1)

    state = GameState(
        hands=hands,
        current_player=2,  # pick someone who likely has plays
        table=table,
        scores=[0] * n_players,
        scout_and_show_tokens=[True] * n_players,
    )

    print_table(state.table)
    print_hands(state.hands, "Before Scout&Show")
    print(f"Scout&Show tokens: {state.scout_and_show_tokens}")

    moves = get_legal_scout_and_show_moves(state)
    print(f"\n=== Scout&Show candidates for P{state.current_player} ===")
    print(f"count: {len(moves)}")
    pprint(moves[:5])

    if not moves:
        print("\nNo Scout&Show moves available (this can happen depending on hand/table).")
        return

    chosen = moves[0]
    print("\n=== Applying Scout&Show candidate ===")
    print(chosen)

    state2 = apply_scout_and_show_move(state, chosen)

    print_table(state2.table)
    print_hands(state2.hands, "After Scout&Show")
    print(f"\nNext player: Player{state2.current_player}")
    print(f"Scores: {state2.scores}")
    print(f"Scout&Show tokens: {state2.scout_and_show_tokens}")