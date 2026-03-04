from dataclasses import dataclass

# Dataclass takes care of a bunch of boilerplate code for defining a class that mainly holds state
# frozen=True so that the object becomes immutable
@dataclass(frozen=True)
class Card:
    side_a: int
    side_b: int
    flipped: bool = False

    @property
    def active(self) -> int:
        """
        Checks and returns the active value of the card. Implemented as a property so it gets treated like an attribute
        Usage: card.active
        """
        return self.side_b if self.flipped else self.side_a

    @property
    def inactive(self) -> int:
        """
        Returns inactive value of a card
        """
        return self.side_a if self.flipped else self.side_b

    def flip_card(self) -> "Card":
        """
        Flips card orientation (by switching the flipped boolean). Returns new card object, since Cards are immutable!
        Usage: card = card.flip_card()
        """
        return Card(self.side_a, self.side_b, not self.flipped)

# List of 2D tuples, represents the cards in a regular scout deck
DECK_PAIRS = [
    (1, 10), (6, 1), (8, 5), (7, 10), (7, 9), (4, 8), (2, 8), (7, 8), (2, 1), (6, 4), (7, 5), (3, 5), (3, 1),
    (7, 3), (5, 6), (10, 4), (8, 3), (2, 6), (1, 9), (5, 2), (4, 9), (10, 9), (7, 1), (4, 5), (3, 9), (2, 4),
    (4, 7), (9, 6), (4, 1), (6, 7), (3, 4), (2, 10), (9, 8), (7, 2), (6, 8), (3, 10), (9, 5), (10, 8), (3, 2),
    (10, 5), (1, 5), (1, 8), (9, 2), (3, 6), (6, 10)
]

def build_deck(rng, n_players):
    """
    Builds a deck of card objects. Randomizing the cards orientations (flipped value) and order based on a random seed
    defined in the main simulation loop.
    :param rng: obtained from random.Random(seed)
    :return: deck, a list of card objects
    """
    if n_players == 3:
        pairs = [pair for pair in DECK_PAIRS if 10 not in pair]
    elif n_players == 4:
        pairs = [pair for pair in DECK_PAIRS if pair != (10, 9)]
    elif n_players == 5:
        pairs = DECK_PAIRS
    else:
        raise ValueError("Game supports 3-5 players only")

    deck = [Card(a, b, flipped=(rng.random() < 0.5)) for (a, b) in pairs]

    rng.shuffle(deck)
    return deck

def deal_hands(deck: list[Card], n_players: int):
    if len(deck) % n_players != 0:
        raise ValueError("Deck size must be divisible by player count")

    hand_size = len(deck) // n_players
    hands = []
    for i in range(n_players):
        start = i * hand_size
        end = (i + 1) * hand_size
        hand = deck[start:end]
        hands.append(hand)

    return hands
