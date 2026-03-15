from engine.state.CardCore import Card
from engine.state.GameState import *
import random
from engine.logic.helpers import determine_show_candidates
from engine.logic.legal_moves import apply_scout_move, get_legal_show_candidates

def display_hand(hand: list[Card]) -> None:
    print(f'Active Values: {[card.active for card in hand]} \n')
    print(f'Inactive Values: {[card.inactive for card in hand]}')

def prompt_yn_decision(prompt: str) -> bool:
    """
    Prompt until user selects yes or no
    """
    while True:
        answer = input(prompt).strip().lower()
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        print("Please type y or n.")

def print_current_state(state: GameState) -> None:
    print('CURRENT GAME STATE')
    print(f'Round {state.round_num} | Current player: P{state.current_player}')
    print(f'Scores: {state.scores}')

    if state.table is None:
        print('Table: (empty)')
    else:
        print(f'Active show on table: {[c.active for c in state.table.cards]}')
        print(f'Inactive table values: {[c.inactive for c in state.table.cards]}')
        print(f'Show played by: P{state.table.played_by}')

def prompt_int_based_decision(prompt: str, low: int, high: int) -> int:
    """
    Prompt until user enters an int in bounds [low, high].
    """
    while True:
        answer = input(prompt).strip()
        if answer.isdigit():
            x = int(answer)
            if low <= x <= high:
                return x
        print(f"Please enter an integer in [{low}, {high}].")

class HumanBot:
    """
    CLI Interface for a human player
    """
    def __init__(self, name: str = "HumanPlayer"):
        self.name = name

    def choose_flip(self, hand: list[Card], player_index: int, rng: random.Random) -> bool:
        print(f'FLIP DECISION for HumanPlayer {self.name}')
        display_hand(hand)
        return prompt_yn_decision('Flip entire hand? [y/n]: ')

    def select_move(self, state: GameState, moves: list[Move], rng: random.Random) -> Move:
        # Show player relevant information
        player = state.current_player
        print_current_state(state)
        print(f"Scout&Show token available for you: {state.scout_and_show_tokens[player]}")
        display_hand(state.hands[player])

        # Sort available move kinds for selection
        has_show = any(isinstance(m, ShowMove) for m in moves)
        has_scout = any(isinstance(m, ScoutMove) for m in moves)
        has_scout_show = any(isinstance(m, ScoutAndShowMove) for m in moves)

        # Build action menu
        options = []
        if has_show:
            options.append("Show")
        if has_scout:
            options.append("Scout")
        if has_scout_show:
            options.append("Scout&Show")

        print("\nChoose action type:")
        for i, label in enumerate(options):
            print(f"[{i}] {label}")

        choice = prompt_int_based_decision(prompt="Action type index: ", low=0, high=len(options) - 1)
        kind = options[choice]

        if kind == "Show":
            return self._choose_show(moves)

        if kind == "Scout":
            return self._choose_scout(state, moves)

        if kind == "Scout&Show":
            return self._choose_scout_and_show(state, moves)

        raise RuntimeError("Invalid action selection state.")

    def _choose_show(self, moves: list[Move]) -> Move:
        show_moves = [m for m in moves if isinstance(m, ShowMove)]
        assert show_moves

        print("\nLegal shows to play:")
        for i, c in enumerate(show_moves):
            print(f" [{i}] Values: {c.candidate.values}")

        idx = prompt_int_based_decision(prompt="\nChoose the show you want to play: ", low=0, high=len(show_moves) - 1)
        return show_moves[idx]

    def _choose_scout(self, state: GameState, moves: list[Move]) -> Move:
        if state.table is None:
            raise RuntimeError("No scout move possible but scout chosen.")

        # Step 1: choose end if there is more than 1 card
        table_len = len(state.table.cards)
        if table_len > 1:
            ends = [("LEFT", state.table.cards[0].active, state.table.cards[0].inactive),
                    ("RIGHT", state.table.cards[-1].active, state.table.cards[-1].inactive)]
            print("\nScout: choose which end card to take:")
            for (end, active, inactive) in ends:
                print(f"  {end}, active value: {active}, inactive value: {inactive}")

            # Decision point (left or right)
            while True:
                chose_left = prompt_yn_decision("Choose LEFT card? [y/n]: ")
                if chose_left:
                    table_index = 0
                    break

                chose_right = prompt_yn_decision("Choose RIGHT card? [y/n]: ")
                if chose_right:
                    table_index = table_len - 1
                    break
        else:
            table_index = 0

        # Step 2: flip decision
        flip = prompt_yn_decision("Flip taken card? [y/n]: ")

        # Step 3: choose insert slot
        hand_len = len(state.hands[state.current_player])
        print("\nChoose insert slot (0..hand_len):")
        print(f"Hand: {[card.active for card in state.hands[state.current_player]]}")
        print("Slots:", " ".join(str(i) for i in range(hand_len + 1)))
        insert_index = prompt_int_based_decision("Insert slot: ", 0, hand_len)

        candidate = ScoutCandidate(table_index=table_index, hand_insert_index=insert_index, flip=flip)
        chosen_move = ScoutMove(candidate)

        if chosen_move not in moves:
            print("\nThat exact scout move isn't in the legal move list (should be rare).")
            print("Try again (maybe the other end is illegal when table_len==1).")
            return self._choose_scout(state, moves)

        return chosen_move

    def _choose_scout_and_show(self, state: GameState, moves: list[Move]) -> Move:
        if state.table is None:
            print("Table is empty: Scout&Show is not legal.")
            raise RuntimeError("No scout&show possible but scout&show chosen.")

        player = state.current_player
        if not state.scout_and_show_tokens[player]:
            print("Scout&Show token already used.")
            raise RuntimeError("Scout&Show chosen but token unavailable.")

        print("SCOUT & SHOW selected")
        scout_move = self._choose_scout(state, moves)
        scout_cand = scout_move.candidate

        # Simulate scout (no advance) to see available shows after scouting
        scout_state = apply_scout_move(state, scout_cand, advance_turn=False)
        show_cands = get_legal_show_candidates(scout_state)

        if not show_cands:
            print("\nAfter that scout, you still have no legal shows to play.")
            print("Choose a different scout (or just Scout instead).")
            return self._choose_scout_and_show(state, moves)

        print("\nNow choose the Show to play after scouting:")
        temp_show_moves = [ShowMove(c) for c in show_cands]
        picked_show_move = self._choose_show(temp_show_moves)  # returns ShowMove
        show_cand = picked_show_move.candidate

        composite = ScoutAndShowCandidate(scout=scout_cand, show=show_cand)
        chosen_move = ScoutAndShowMove(composite)

        if chosen_move not in moves:
            print("\nThat Scout&Show combo is not present in legal move list (should be rare).")
            print("Try again.")
            return self._choose_scout_and_show(state, moves)

        return chosen_move
