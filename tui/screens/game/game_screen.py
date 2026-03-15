import random
from typing import Optional, List, Set
from enum import Enum, auto

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Static, Button
from textual.containers import Vertical, Horizontal
from textual.binding import Binding

from engine.state.simulation_core import build_deck, deal_hands, Card
from engine.state.GameState import GameState, ShowMove, ScoutMove, ScoutAndShowMove
from engine.logic.legal_moves import get_all_legal_moves, apply_move
from engine.logic.helpers import flip_entire_hand, any_empty_hand, unbeaten_show_cycle, apply_end_of_round_penalties
from players.Bots import RandomBot
from ...render_cards import render_card_row

from .widgets import GameLog, PlayerSummary
from .flip_screen import FlipScreen

class GamePhase(Enum):
    FLIP_DECISION = auto()
    ACTION_CHOICE = auto()         # Main turn start: Choose Show, Scout, or SAS
    SHOW_SELECT = auto()           # Selecting cards for Show
    SCOUT_CARD_SELECT = auto()     # If table has multiple cards, choose one
    SCOUT_INSERT_POS = auto()      # Choosing where to put the scouted card
    SCOUT_INSERT_ORIENTATION = auto() # Choosing orientation of scouted card
    ROUND_OVER = auto()

class GameScreen(Screen):
    """The modular interactive Gameplay Screen."""
    
    BINDINGS = [
        Binding("left", "cursor_left", "Cursor Left", show=False),
        Binding("right", "cursor_right", "Cursor Right", show=False),
        Binding("space", "toggle_selection", "Select", show=False),
        Binding("enter", "confirm_action", "Confirm", show=False),
        Binding("escape", "cancel_action", "Cancel", show=False),
        # Action Shortcuts
        Binding("s", "choose_show", "Show", show=False),
        Binding("c", "choose_scout", "Scout", show=False),
        Binding("a", "choose_sas", "Scout & Show", show=False),
    ]

    can_focus = True

    def __init__(self, config):
        super().__init__()
        self.config = config
        self.rng = random.Random(config.seed)
        self.game_state: Optional[GameState] = None
        
        self.phase = GamePhase.ACTION_CHOICE
        self.cursor_index = 0
        self.selected_indices: Set[int] = set()
        self.legal_moves = []
        self.scouted_table_index: Optional[int] = None # Which card from table we pick
        self.is_sas_flow = False # Flag for Scout & Show sequence
        self.sas_scout_candidate: Optional[any] = None # Temp storage for SAS scout part
        
        self.bots = []
        for t in config.seat_types:
            if t == "random":
                self.bots.append(RandomBot())
            else:
                self.bots.append(None)

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="game_top_bar"):
            yield Static("SCOUT BOT", id="game_title")
            yield Static("Round: 1", id="game_status")
            yield Button("Exit", id="exit_game", variant="error")
        
        with Horizontal(id="game_main"):
            with Vertical(id="play_area"):
                yield Static("TABLE", classes="header")
                yield Static("(Table)", id="table_area")
                yield Static("YOUR HAND", classes="header")
                yield Static("(Hand)", id="hand_area")
                yield Static("Use Arrow Keys to move cursor, Space to select, Enter to confirm.", id="interaction_hint")

                with Horizontal(id="game_controls"):
                    yield Button("Show", id="btn_show", variant="primary")
                    yield Button("Scout", id="btn_scout")
                    yield Button("Scout & Show", id="btn_scout_show")

            with Vertical(id="side_panel"):
                yield Static("PLAYERS", classes="header")
                yield PlayerSummary(id="player_summary")
                yield Static("RESOURCES", classes="header")
                yield Static("Tokens: ...", id="resource_info")

            with Vertical(id="log_panel"):
                yield Static("GAME LOG", classes="header")
                yield GameLog(id="game_log")
        
        yield Footer()

    def on_mount(self) -> None:
        # Fix NoMatches: Configure focus in on_mount, NOT compose
        for btn_id in ["#exit_game", "#btn_show", "#btn_scout", "#btn_scout_show"]:
            self.query_one(btn_id, Button).can_focus = False

        self.focus() # Ensure screen handles bindings
        self.logger.log_info("Welcome to ScoutBot!")
        self.start_game()

    @property
    def logger(self) -> GameLog:
        return self.query_one("#game_log", GameLog)

    def start_game(self) -> None:
        self.logger.log_round_start(1, self.config.n_players)
        deck = build_deck(self.rng, n_players=self.config.n_players)
        hands = deal_hands(deck, n_players=self.config.n_players)
        
        self.game_state = GameState(
            hands=hands,
            current_player=0,
            table=None,
            scores=[0] * self.config.n_players,
            scout_and_show_tokens=[True] * self.config.n_players,
            round_num=1,
            start_player=0
        )
        
        self.phase = GamePhase.FLIP_DECISION
        self.logger.log_phase("Hand Flip Decision")
        self.update_ui()
        self.check_initial_flip()

    def check_initial_flip(self) -> None:
        cur_player = self.game_state.current_player
        if self.bots[cur_player]:
            self.logger.log_info(f"P{cur_player} (Bot) keeps hand.")
            self.begin_turn()
        else:
            hand = self.game_state.hands[cur_player]
            self.app.push_screen(FlipScreen(hand), self.handle_flip_result)

    def handle_flip_result(self, flipped: bool) -> None:
        if flipped:
            cur_player = self.game_state.current_player
            new_hands = list(self.game_state.hands)
            new_hands[cur_player] = flip_entire_hand(new_hands[cur_player])
            self.game_state = GameState(
                hands=new_hands,
                current_player=self.game_state.current_player,
                table=self.game_state.table,
                scores=self.game_state.scores,
                scout_and_show_tokens=self.game_state.scout_and_show_tokens,
                round_num=self.game_state.round_num,
                start_player=self.game_state.start_player,
                last_show_player=self.game_state.last_show_player
            )
            self.logger.log_info("You flipped your hand!")
        else:
            self.logger.log_info("You kept your hand.")
        self.begin_turn()

    def update_ui(self) -> None:
        if not self.game_state:
            return

        self.query_one("#game_status", Static).update(f"Round: {self.game_state.round_num}")
        
        table_area = self.query_one("#table_area", Static)
        table_cursor = set()
        if self.phase == GamePhase.SCOUT_CARD_SELECT:
            table_cursor = {self.cursor_index}
            
        if self.game_state.table:
            table_area.update(render_card_row(list(self.game_state.table.cards), cursor_indices=table_cursor))
        else:
            table_area.update("\n\n[dim](Empty Table)[/]")

        hand_area = self.query_one("#hand_area", Static)
        cur_player = self.game_state.current_player
        hand = self.game_state.hands[cur_player]
        
        is_human = self.bots[cur_player] is None
        hint = self.query_one("#interaction_hint", Static)

        if is_human:
            hand_cursor = set()
            if self.phase == GamePhase.SHOW_SELECT:
                hand_cursor = {self.cursor_index}
                hand_area.update(render_card_row(hand, selected_indices=self.selected_indices, cursor_indices=hand_cursor))
                hint.update("Select cards (Arrow Keys + Space), then [bold]Enter[/] to confirm.")
            elif self.phase == GamePhase.SCOUT_INSERT_POS:
                # Highlighting for insertion slots (between cards)
                if self.cursor_index == 0:
                    hand_cursor = {0}
                elif self.cursor_index == len(hand):
                    hand_cursor = {len(hand) - 1}
                else:
                    hand_cursor = {self.cursor_index - 1, self.cursor_index}
                
                hand_area.update(render_card_row(hand, cursor_indices=hand_cursor))
                hint.update("Move cursor to insertion point (between cards), then [bold]Enter[/].")
            elif self.phase == GamePhase.SCOUT_CARD_SELECT:
                hand_area.update(render_card_row(hand))
                hint.update("Choose card to scout from table (Ends only), then [bold]Enter[/].")
            elif self.phase == GamePhase.ACTION_CHOICE:
                hand_area.update(render_card_row(hand))
                hint.update("Choose: [bold]S[/]how, [bold]C[/]scout, or [bold]A[/]scout&show")
            elif self.phase == GamePhase.SCOUT_INSERT_ORIENTATION:
                hand_area.update(render_card_row(hand))
                hint.update("Choose orientation: [bold]Y[/] (Keep) or [bold]N[/] (Flip).")
            else:
                hand_area.update(render_card_row(hand))
            
            hint.visible = True
        else:
            if self.config.show_bot_hands:
                hand_area.update(f"\n[dim]Player {cur_player} is thinking...[/]\n" + render_card_row(hand))
            else:
                hand_area.update(f"\n\n[dim]Player {cur_player} is thinking...[/]\n[italic](Hand Hidden: {len(hand)} cards)[/]")
            hint.visible = False

        self.query_one("#player_summary", PlayerSummary).update_summary(self.game_state, self.bots, cur_player)
        
        tokens = self.game_state.scout_and_show_tokens[cur_player]
        self.query_one("#resource_info", Static).update(f"Scout & Show Token: {'[green]Available[/]' if tokens else '[red]Used[/]'}")

    def begin_turn(self) -> None:
        if any_empty_hand(self.game_state) or unbeaten_show_cycle(self.game_state):
            self.end_round()
            return

        self.phase = GamePhase.ACTION_CHOICE
        self.cursor_index = 0
        self.selected_indices = set()
        self.scouted_table_index = None
        self.is_sas_flow = False
        self.sas_scout_candidate = None
        self.legal_moves = get_all_legal_moves(self.game_state)
        self.update_ui()
        
        cur_player = self.game_state.current_player
        bot = self.bots[cur_player]
        
        if bot:
            self.set_controls_enabled(False)
            self.set_timer(1.2, self.run_bot_turn)
        else:
            self.set_controls_enabled(True)

    def set_controls_enabled(self, enabled: bool) -> None:
        self.query_one("#btn_show", Button).disabled = not enabled
        can_scout = any(isinstance(m, ScoutMove) for m in self.legal_moves)
        can_sas = any(isinstance(m, ScoutAndShowMove) for m in self.legal_moves)
        self.query_one("#btn_scout", Button).disabled = not enabled or not can_scout
        self.query_one("#btn_scout_show", Button).disabled = not enabled or not can_sas

    def run_bot_turn(self) -> None:
        moves = get_all_legal_moves(self.game_state)
        bot = self.bots[self.game_state.current_player]
        chosen = bot.select_move(self.game_state, moves, self.rng)
        
        self.logger.log_move(self.game_state.current_player, chosen, is_bot=True)
        
        self.game_state = apply_move(self.game_state, chosen)
        self.begin_turn()

    def end_round(self) -> None:
        self.phase = GamePhase.ROUND_OVER
        unbeaten = unbeaten_show_cycle(self.game_state)
        scores_out = apply_end_of_round_penalties(self.game_state, unbeaten)
        
        reason = "No one could beat the show." if unbeaten else "Someone emptied their hand."
        self.logger.log_round_end(reason, scores_out)
        self.update_ui()

    # Action Selection Logic
    def action_choose_show(self) -> None:
        if self.phase == GamePhase.ACTION_CHOICE:
            if self.selected_indices:
                self.try_show()
            else:
                self.phase = GamePhase.SHOW_SELECT
                self.update_ui()

    def action_choose_scout(self) -> None:
        if self.phase == GamePhase.ACTION_CHOICE:
            self.start_scout_flow()

    def action_choose_sas(self) -> None:
        if self.phase == GamePhase.ACTION_CHOICE:
            sas_moves = [m for m in self.legal_moves if isinstance(m, ScoutAndShowMove)]
            if not sas_moves:
                self.logger.log_error("Scout & Show not legal right now!")
                return
            self.is_sas_flow = True
            self.start_scout_flow()

    # Input Handlers
    def action_cursor_left(self) -> None:
        if self.phase == GamePhase.SCOUT_CARD_SELECT:
            self.cursor_index = 0
            self.update_ui()
        elif self.phase in [GamePhase.SHOW_SELECT, GamePhase.SCOUT_INSERT_POS]:
            hand_len = len(self.game_state.hands[self.game_state.current_player])
            limit = hand_len + 1 if self.phase == GamePhase.SCOUT_INSERT_POS else hand_len
            self.cursor_index = (self.cursor_index - 1) % limit
            self.update_ui()

    def action_cursor_right(self) -> None:
        if self.phase == GamePhase.SCOUT_CARD_SELECT:
            self.cursor_index = len(self.game_state.table.cards) - 1
            self.update_ui()
        elif self.phase in [GamePhase.SHOW_SELECT, GamePhase.SCOUT_INSERT_POS]:
            hand_len = len(self.game_state.hands[self.game_state.current_player])
            limit = hand_len + 1 if self.phase == GamePhase.SCOUT_INSERT_POS else hand_len
            self.cursor_index = (self.cursor_index + 1) % limit
            self.update_ui()

    def action_toggle_selection(self) -> None:
        if self.phase == GamePhase.SHOW_SELECT:
            if self.cursor_index in self.selected_indices:
                self.selected_indices.remove(self.cursor_index)
            else:
                self.selected_indices.add(self.cursor_index)
            self.update_ui()

    def action_confirm_action(self) -> None:
        try:
            if self.phase == GamePhase.SHOW_SELECT:
                self.try_show()
            elif self.phase == GamePhase.SCOUT_CARD_SELECT:
                self.scouted_table_index = self.cursor_index
                self.phase = GamePhase.SCOUT_INSERT_POS
                self.cursor_index = 0
                self.update_ui()
            elif self.phase == GamePhase.SCOUT_INSERT_POS:
                self.phase = GamePhase.SCOUT_INSERT_ORIENTATION
                self.logger.log_info("Orientation: Press Y (Keep) or N (Flip)")
                self.update_ui()
            elif self.phase == GamePhase.ACTION_CHOICE:
                # If they already selected cards and hit enter, maybe they mean 'Show'?
                if self.selected_indices:
                    self.action_choose_show()
                else:
                    self.logger.log_info("Choose an action first (S/C/A)")
            else:
                self.logger.log_info(f"Action confirm ignored in phase: {self.phase}")
        except Exception as e:
            self.logger.log_error(f"Error during confirm: {e}")
            import traceback
            self.logger.log_info(traceback.format_exc())

    def action_cancel_action(self) -> None:
        if self.phase in [GamePhase.SHOW_SELECT, GamePhase.SCOUT_CARD_SELECT, GamePhase.SCOUT_INSERT_POS, GamePhase.SCOUT_INSERT_ORIENTATION]:
            self.phase = GamePhase.ACTION_CHOICE
            self.selected_indices = set()
            self.cursor_index = 0
            self.is_sas_flow = False
            self.sas_scout_candidate = None
            self.logger.log_info("Action cancelled.")
            self.update_ui()

    def on_key(self, event) -> None:
        k = event.key.lower()
        if self.phase == GamePhase.SCOUT_INSERT_ORIENTATION:
            if k in ['y', 'u', 'up']:
                self.finalize_scout(flipped=False)
            elif k in ['n', 'd', 'down']:
                self.finalize_scout(flipped=True)

    def try_show(self) -> None:
        if not self.selected_indices: 
            self.logger.log_info("No cards selected! Select contiguous cards with SPACE first.")
            return

        start = min(self.selected_indices)
        length = max(self.selected_indices) - start + 1
        
        if len(self.selected_indices) != length:
            self.logger.log_error("Invalid Selection: Cards must be contiguous.")
            return
            
        matching_move = None
        if self.is_sas_flow:
            from engine.state.GameState import ScoutAndShowCandidate
            sas_moves = [m for m in self.legal_moves if isinstance(m, ScoutAndShowMove)]
            for m in sas_moves:
                if (m.candidate.scout == self.sas_scout_candidate and 
                    m.candidate.show.start == start and 
                    m.candidate.show.length == length):
                    matching_move = m
                    break
        else:
            for m in self.legal_moves:
                if isinstance(m, ShowMove) and m.candidate.start == start and m.candidate.length == length:
                    matching_move = m
                    break
        
        if matching_move:
            self.logger.log_move(self.game_state.current_player, matching_move, is_bot=False)
            
            self.game_state = apply_move(self.game_state, matching_move)
            self.begin_turn()
        else:
            # Fallback for error messages
            self.logger.log_error("Move rejected! (Invalid pattern or doesn't beat table)")


    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        if event.button.id == "exit_game":
            self.app.pop_screen()
        elif event.button.id == "btn_show":
            self.action_choose_show()
        elif event.button.id == "btn_scout":
            self.action_choose_scout()
        elif event.button.id == "btn_scout_show":
            self.action_choose_sas()

    def handle_scout_and_show(self) -> None:
        self.logger.log_info("Scout & Show button pressed. Not fully implemented in UI yet.")
        self.notify("Scout & Show is not yet implemented.")

    def start_scout_flow(self) -> None:
        if self.is_sas_flow:
            # For SAS, we need to filter legal moves to only those that are SAS moves
            moves_to_consider = [m for m in self.legal_moves if isinstance(m, ScoutAndShowMove)]
            if not moves_to_consider:
                self.logger.log_error("No legal Scout & Show moves available.")
                self.action_cancel_action()
                return
            # Extract unique scout candidates from SAS moves
            scout_candidates = {m.candidate.scout for m in moves_to_consider}
            table_indices = {s.table_index for s in scout_candidates}
        else:
            # For normal Scout, filter for Scout moves
            moves_to_consider = [m for m in self.legal_moves if isinstance(m, ScoutMove)]
            if not moves_to_consider:
                self.logger.log_error("No legal Scout moves available.")
                self.action_cancel_action()
                return
            # Extract unique scout candidates from Scout moves
            scout_candidates = {m.candidate for m in moves_to_consider}
            table_indices = {s.table_index for s in scout_candidates}
        
        # Check if we need to choose which card to scout from the table
        if len(table_indices) > 1:
            self.phase = GamePhase.SCOUT_CARD_SELECT
            self.cursor_index = min(table_indices) # Usually 0
            self.logger.log_info("Scouting... Choose card from table (Ends only).")
        else:
            self.scouted_table_index = next(iter(table_indices))
            self.phase = GamePhase.SCOUT_INSERT_POS
            self.cursor_index = 0
            self.logger.log_info(f"Scouting card from table (Index {self.scouted_table_index})...")
        
        self.update_ui()

    def finalize_scout(self, flipped: bool) -> None:
        # We need to find a scout candidate that matches table_index, insert_index, and flip
        from engine.state.GameState import ScoutCandidate
        cand = ScoutCandidate(
            table_index=self.scouted_table_index,
            hand_insert_index=self.cursor_index,
            flip=flipped
        )
        
        if self.is_sas_flow:
            # Check if any SAS move uses this scout candidate
            sas_moves = [m for m in self.legal_moves if isinstance(m, ScoutAndShowMove)]
            valid_cand = any(m.candidate.scout == cand for m in sas_moves)
            if valid_cand:
                self.sas_scout_candidate = cand
                self.phase = GamePhase.SHOW_SELECT
                self.cursor_index = 0
                self.selected_indices = set()
                self.logger.log_info("Scouted! Now Select Cards to show (contiguous).")
                self.update_ui()
            else:
                self.logger.log_error("This scout move is not part of any legal Scout & Show.")
                self.action_cancel_action()
            return

        # Normal Scout Flow
        scout_moves = [m for m in self.legal_moves if isinstance(m, ScoutMove)]
        matching_move = next((m for m in scout_moves if m.candidate == cand), None)
        
        if matching_move:
            self.logger.log_move(self.game_state.current_player, matching_move, is_bot=False)
            self.game_state = apply_move(self.game_state, matching_move)
            self.begin_turn()
        else:
            self.logger.log_error("That scout move is not legal.")
            self.action_cancel_action()
