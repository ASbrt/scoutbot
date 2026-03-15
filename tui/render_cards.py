from engine.state.simulation_core import Card

def card_values_active_inactive(card: Card) -> tuple[int, int]:
    # Adjust if your Card uses different names
    if card.flipped:
        return card.side_b, card.side_a
    return card.side_a, card.side_b

def _fmt_val(v: int, width: int = 2) -> str:
    """
    Fixed-width formatting for values 1..10 (10 becomes '10', others ' 8', etc.).
    width=2 yields 2-char field.
    """
    s = str(v)
    return s.rjust(width)

def render_card(card: Card) -> list[str]:
    """
    Render a single Scout card with active/inactive values.
    Returns a list of equal-width strings (same line length).
    """
    a, b = card_values_active_inactive(card)

    # Using width=2 gives us nice alignment for 10
    active_value = _fmt_val(a, 2)
    inactive_value = _fmt_val(b, 2)

    # total width here is 6 chars: "┌────┐"
    top    = "┌────┐"
    midsep = "├────┤"
    bottom = "└────┘"

    line_a = f"│ {active_value} │"
    line_b = f"│ {inactive_value} │"

    return [top, line_a, midsep, line_b, bottom]

def render_card_row(cards: list[Card], gap: str = " ", selected_indices: set[int] = None, cursor_indices: set[int] = None) -> str:
    """
    Render multiple cards in one row as a single multi-line string.
    :param cards: List of Card objects
    :param gap: Space between cards
    :param selected_indices: Set of indices to highlight as selected
    :param cursor_indices: Set of indices under the cursor (for multi-card highlights like insertion)
    """
    if not cards:
        return "(none)"

    selected_indices = selected_indices or set()
    cursor_indices = cursor_indices or set()
    blocks = [
        render_card_lines(c, selected=(i in selected_indices), cursor=(i in cursor_indices)) 
        for i, c in enumerate(cards)
    ]
    height = len(blocks[0])

    lines = []
    for i in range(height):
        lines.append(gap.join(block[i] for block in blocks))
    return "\n".join(lines)

def render_card_lines(card: Card, selected: bool = False, cursor: bool = False) -> list[str]:
    vals = card_values_active_inactive(card)
    v_top = str(vals[0]).rjust(2)
    v_bot = str(vals[1]).ljust(2)

    # Base Border Characters (bold single)
    b_top, b_mid, b_bot, b_side = "┏━━━┓", "┣━━━┫", "┗━━━┛", "┃"
    
    # Text Styles
    color_start = ""
    color_end = ""

    if selected:
        # Selection Uses Double Borders
        b_top, b_mid, b_bot, b_side = "╔═══╗", "╠═══╣", "╚═══╝", "║"
        color_start = "[bold cyan]"
        color_end = "[/]"

    if cursor:
        # Cursor adds a thick block border character elsewhere? 
        # No, let's use reverse style for the WHOLE card area if cursor is on it
        color_start = "[bold reverse magenta]" if not selected else "[bold reverse cyan]"
        color_end = "[/]"

    # Construct lines
    top = f"{color_start}{b_top}{color_end}"
    s_c = f"{color_start}{b_side}{color_end}"
    
    line_a = f"{s_c}{v_top} {s_c}"
    mid    = f"{color_start}{b_mid}{color_end}"
    line_b = f"{s_c} {v_bot}{s_c}"
    bot    = f"{color_start}{b_bot}{color_end}"

    if cursor:
        cursor_ind = "[yellow]  ^  [/]"
    else:
        cursor_ind = "     "

    return [top, line_a, mid, line_b, bot, cursor_ind]