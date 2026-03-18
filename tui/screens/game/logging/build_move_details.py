"""Helpers for building move narration. Extracts information from move objects"""

from typing import Optional

from engine.logic.legal_moves import apply_scout_move
from engine.state.CardCore import Card
from engine.state.GameState import GameState, Move, ScoutAndShowMove, ScoutMove, ShowMove


def build_move_details(player: int, move: Move, state_before: GameState, state_after: GameState) -> dict:
    """Assemble move details used by GameLog for narration. Branches to handle move-types"""
    score_delta = [after - before for before, after in zip(state_before.scores, state_after.scores)]

    if isinstance(move, ShowMove):
        start = move.candidate.start
        end = start + move.candidate.length
        return {
            # Slice from the pre-move hand so the log shows the cards that were
            # actually played, not the shortened hand after resolution.
            "cards": tuple(state_before.hands[player][start:end]),
            "score_delta": score_delta,
        }

    if isinstance(move, ScoutMove):
        scout_card = _scouted_card_from_state(state_before, move.candidate.table_index)
        return {
            "scout_card": scout_card,
            # For handling orientation
            "scout_result_card": scout_card.flip_card() if scout_card and move.candidate.flip else scout_card,
            "score_delta": score_delta,
        }

    if isinstance(move, ScoutAndShowMove):
        # Combined branch
        scout_card = _scouted_card_from_state(state_before, move.candidate.scout.table_index)
        scout_state = apply_scout_move(state_before, move.candidate.scout, advance_turn=False)
        start = move.candidate.show.start
        end = start + move.candidate.show.length
        return {
            "scout_card": scout_card,
            "scout_result_card": scout_card.flip_card() if scout_card and move.candidate.scout.flip else scout_card,
            "cards": tuple(scout_state.hands[player][start:end]),
            "score_delta": score_delta,
        }

    return {"score_delta": score_delta}


def _scouted_card_from_state(state: GameState, table_index: int) -> Optional[Card]:
    """Reads the original card from the pre-move table for narration."""
    if state.table is None or table_index >= len(state.table.cards):
        return None
    return state.table.cards[table_index]
