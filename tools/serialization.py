from engine.state.CardCore import Card
from engine.state.GameState import GameState
from engine.state.GameState import ShowMove, ScoutMove, ScoutAndShowMove


def serialize_player_type(actor) -> str:
    if actor is None:
        return "Human"
    return actor.__class__.__name__


def serialize_seat_types(bots: list) -> list[str]:
    return [serialize_player_type(actor) for actor in bots]


def serialize_card(card: Card) -> dict:
    return {
        "side_a": card.side_a,
        "side_b": card.side_b,
        "flipped": card.flipped,
        "active": card.active
    }

def serialize_show(show) -> dict | None:
    if show is None:
        return None

    return {
        "played_by": show.played_by,
        "kind": show.kind,
        "rank": show.rank,
        "cards": [serialize_card(c) for c in show.cards]
    }

def serialize_game_state(state: GameState) -> dict:
    return {
        "hands": [[serialize_card(card) for card in hand] for hand in state.hands],
        "current_player": state.current_player,
        "table": serialize_show(state.table),
        "scores": list(state.scores),
        "scout_and_show_tokens": list(state.scout_and_show_tokens),
        "round_num": state.round_num,
        "start_player": state.start_player,
        "last_show_player": state.last_show_player
    }

def serialize_move(move) -> dict:

    if isinstance(move, ShowMove):
        c = move.candidate
        return {
            "move_type": "ShowMove",
            "start": c.start,
            "length": c.length,
            "kind": c.kind,
            "values": list(c.values),
        }

    elif isinstance(move, ScoutMove):
        c = move.candidate
        return {
            "move_type": "ScoutMove",
            "table_index": c.table_index,
            "hand_insert_index": c.hand_insert_index,
            "flip": c.flip,
        }

    elif isinstance(move, ScoutAndShowMove):
        s = move.candidate.scout
        sh = move.candidate.show

        return {
            "move_type": "ScoutAndShowMove",
            "scout": {
                "table_index": s.table_index,
                "hand_insert_index": s.hand_insert_index,
                "flip": s.flip,
            },
            "show": {
                "start": sh.start,
                "length": sh.length,
                "kind": sh.kind,
                "values": list(sh.values),
            },
        }

    else:
        raise TypeError(f"Wrong move type passed to serialization: {type(move)}")
