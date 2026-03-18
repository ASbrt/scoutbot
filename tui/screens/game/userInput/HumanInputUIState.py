"""State machine for building human moves."""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional
from engine.state.GameState import ScoutCandidate


class HumanTurnPhase(Enum):
    """Sub-phases for building a human move."""

    ACTION_CHOICE = auto()
    SHOW_SELECT = auto()
    SCOUT_CARD_SELECT = auto()
    SCOUT_INSERT_POS = auto()
    SCOUT_INSERT_ORIENTATION = auto()


@dataclass
class TurnInputState:
    """Transient input state owned by GameScreen"""

    phase: HumanTurnPhase = HumanTurnPhase.ACTION_CHOICE
    cursor_index: int = 0
    selected_indices: set[int] = field(default_factory=set)
    scouted_table_index: Optional[int] = None
    scout_flip: bool = False
    is_scout_and_show: bool = False
    sas_scout_candidate: Optional[ScoutCandidate] = None

    def reset(self) -> None:
        """Return to a clean action-choice state for the next human turn."""
        self.phase = HumanTurnPhase.ACTION_CHOICE
        self.cursor_index = 0
        self.selected_indices.clear()
        self.scouted_table_index = None
        self.scout_flip = False
        self.is_scout_and_show = False
        self.sas_scout_candidate = None

    def start_show_select(self) -> None:
        """Begin the UI flow for selecting contiguous cards to show."""
        self.phase = HumanTurnPhase.SHOW_SELECT
        self.cursor_index = 0
        self.selected_indices.clear()

    def start_scout_flow(self, *, is_scout_and_show: bool) -> None:
        """Begin scout targeting, optionally as the first half of Scout & Show."""
        self.phase = HumanTurnPhase.SCOUT_CARD_SELECT
        self.cursor_index = 0
        self.selected_indices.clear()
        self.scouted_table_index = None
        self.scout_flip = False
        self.is_scout_and_show = is_scout_and_show
        self.sas_scout_candidate = None

    def start_scout_insert(self, table_index: int) -> None:
        """Lock in the table card and move to hand insertion selection."""
        self.phase = HumanTurnPhase.SCOUT_INSERT_POS
        self.cursor_index = 0
        # The chosen table card remains fixed while the player picks insertion
        # position and final orientation.
        self.scouted_table_index = table_index

    def start_orientation_select(self) -> None:
        """Move from insertion-position picking to orientation picking."""
        self.phase = HumanTurnPhase.SCOUT_INSERT_ORIENTATION
        self.scout_flip = False

    def start_scout_and_show_select(self, scout_candidate: ScoutCandidate) -> None:
        """Store the validated scout half and continue into show selection."""
        self.phase = HumanTurnPhase.SHOW_SELECT
        self.cursor_index = 0
        self.selected_indices.clear()
        # Remember the scout half so `_try_show()` can match the final selection
        # against the controller-provided Scout&Show moves.
        self.sas_scout_candidate = scout_candidate

    def toggle_scout_flip(self) -> None:
        """Toggle the orientation preview of the selected scout card."""
        self.scout_flip = not self.scout_flip

    def cancel(self) -> None:
        """Cancel the current UI flow and return to the neutral action state."""
        self.reset()
