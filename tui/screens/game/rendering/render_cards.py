"""Helpers for rendering Scout cards as fixed-width Rich/Textual markup. Essentially an adaptation of this project
 https://github.com/naivoder/ascii_cards/tree/main """

from engine.state.CardCore import Card


def card_values_active_inactive(card: Card) -> tuple[int, int]:
    """Return the currently visible value first, then the hidden value."""
    if card.flipped:
        return card.side_b, card.side_a
    return card.side_a, card.side_b


def _fmt_val(v: int, width: int = 2) -> str:
    """Format one card value into a fixed-width field."""
    return str(v).rjust(width)


def render_card(card: Card) -> list[str]:
    """Render a single Scout card with active/inactive values."""
    active_value, inactive_value = card_values_active_inactive(card)

    # Two-character padding keeps 10 aligned with single-digit values.
    active_text = _fmt_val(active_value, 2)
    inactive_text = _fmt_val(inactive_value, 2)

    # The box is intentionally tiny so multiple cards still fit across the TUI.
    top = "┌────┐"
    middle_separator = "├────┤"
    bottom = "└────┘"

    return [
        top,
        f"│ {active_text} │",
        middle_separator,
        f"│ {inactive_text} │",
        bottom,
    ]


def render_card_row(
    cards: list[Card],
    gap: str = " ",
    selected_indices: set[int] | None = None,
    cursor_indices: set[int] | None = None,
) -> str:
    """Render multiple cards in one row as a single multi-line string."""
    if not cards:
        return "(none)"

    selected_indices = selected_indices or set()
    cursor_indices = cursor_indices or set()
    blocks = [
        render_card_lines(
            card,
            selected=index in selected_indices,
            cursor=index in cursor_indices,
        )
        for index, card in enumerate(cards)
    ]

    lines: list[str] = []
    for row_index in range(len(blocks[0])):
        lines.append(gap.join(block[row_index] for block in blocks))
    return "\n".join(lines)


def render_card_lines(card: Card, selected: bool = False, cursor: bool = False) -> list[str]:
    """Render one card with optional selection and cursor styling."""
    active_value, inactive_value = card_values_active_inactive(card)
    active_text = str(active_value).rjust(2)
    inactive_text = str(inactive_value).ljust(2)

    # Base styling is the default "plain card" look.
    top_border, mid_border, bottom_border, side_border = "┏━━━┓", "┣━━━┫", "┗━━━┛", "┃"
    color_start = ""
    color_end = ""

    if selected:
        # Selection gets stronger borders so multi-card shows are easy to read.
        top_border, mid_border, bottom_border, side_border = "╔═══╗", "╠═══╣", "╚═══╝", "║"
        color_start = "[bold cyan]"
        color_end = "[/]"

    if cursor:
        # Cursor is transient UI state, so reverse-video reads more clearly than
        # introducing yet another border style.
        color_start = "[bold reverse magenta]" if not selected else "[bold reverse cyan]"
        color_end = "[/]"

    top = f"{color_start}{top_border}{color_end}"
    side = f"{color_start}{side_border}{color_end}"
    middle = f"{color_start}{mid_border}{color_end}"
    bottom = f"{color_start}{bottom_border}{color_end}"

    if cursor:
        # The caret gives insertion-position style feedback below the active card.
        cursor_indicator = "[yellow]  ^  [/]"
    else:
        cursor_indicator = "     "

    return [
        top,
        f"{side}{active_text} {side}",
        middle,
        f"{side} {inactive_text}{side}",
        bottom,
        cursor_indicator,
    ]
