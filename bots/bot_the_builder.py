"""
Builds bots and seat options so they can be used in Tournaments and passed through SetupScreen into the GameSession.
Can be extended with future bot versions.

The Monte Carlo bot is commented out because it takes way to long to make a decision in its current form. You can
activate and play against it, by removing the comment, but it is not the best experience. The TUI freezes, and you have
to wait for a while until the rollouts in the back are finished - it works. It just does not work well yet.
"""

from bots.BaseBot import BaseBot
from bots.RandomBot import RandomBot
from bots.HeuristicBots.AggrHeuristicBot import AggrHeuristicBot
from bots.MonteCarloBot.MCBot import MCBot

BOT_CLASSES = [
    RandomBot,
    AggrHeuristicBot,
    # MCBot,
]

# TODO: Dynamic Bot discovery?? Not needed now, but if there are more bots?

# For importing in SetupScreen
def get_lobby_seat_options() -> list[tuple[str, str]]:
    options = [("Human", "human")]
    for bot_class in BOT_CLASSES:
        options.append((bot_class.bot_label, bot_class.bot_key))
    return options

# For importing in bot tournaments
def get_tournament_seat_options() -> list[tuple[str, str]]:
    options = []
    for bot_class in BOT_CLASSES:
        options.append((bot_class.bot_label, bot_class.bot_key))
    return options

def build_a_bot(bot_key: str, **kwargs) -> BaseBot:
    for bot_class in BOT_CLASSES:
        if bot_class.bot_key == bot_key:
            return bot_class(**kwargs)

    raise ValueError(f"Bot Builder received unknown bot key: {bot_key}")

def build_bots_from_wishlist(wishlist: list[tuple[str, dict]]) -> list[BaseBot]:
    bots = []
    for bot_key, kwargs in wishlist:
        bot = build_a_bot(bot_key, **kwargs)
        bots.append(bot)
    return bots