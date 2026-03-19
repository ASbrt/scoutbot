"""
Just a file to think about whether optimizing hand quality by rank might always be the correct policy for
flip decisions.

Answer: it is not necessarily. Flexibility matters in the sense that playing moves in the right order can make your
hand stronger by connecting previously unconnected cards (extending runs and sets).
"""

import random
from engine.state.CardCore import build_deck, deal_hands
from engine.logic.helpers import compute_hand_rank, flip_entire_hand

def main():
    n_players = 3

    deck = build_deck(rng=random.Random(), n_players=n_players)
    hands = deal_hands(deck=deck, n_players=n_players)

    for hand in hands:
        active_set = [c.active for c in hand]
        inactive_set = [c.inactive for c in hand]

        flipped_hand = flip_entire_hand(hand)

        rank_active = compute_hand_rank(hand)
        rank_inactive = compute_hand_rank(flipped_hand)


        print(f"Active Set values: \n{active_set} \nRank: {rank_active}\n")
        print(f"Inactive Set values: \n{inactive_set} \nRank: {rank_inactive}\n")



if __name__ == "__main__":
    main()
