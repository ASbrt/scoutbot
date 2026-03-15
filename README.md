# Scoutbot
Welcome to my project for ICSS! This project implements a game engine for the card game **Scout**. This is meant to work as a basis to explore Monte Carlo Tree Searches as well as learn about general ML techniques.

**IMPORTANT:** This is a work in progress! The current implementation needs a bigger refactor to make TUI work for player input. Which means refactoring the current GameLoop.py into a more modular Controller based system able to handle both event driven and simulation based game loops.

## What is Scout?
Scout is a card game where you can't reorder your hand. You have to play sets or runs to beat what's on the table (**Show**), or take a card from the table to improve your hand (**Scout**). All cards have 2 values on them where only one is active at a time. The basic rules are simple, but the strategy is deep. 

## How the Code Works 
I've organized the project into several folders to keep things tidy. Here's a breakdown of what each part does:

### 1. `engine/` (The Brains)
This is where all the game rules live.
- **`engine/state/`**: Definitions for `GameState` and `Card`.
- **`engine/logic/`**: The "referee" code that knows about `legal_moves` and the `GameLoop`.

### 2. `tui/` (The Face)
This is the new interactive terminal interface! It handles:
- **Home Screen**: Navigation to Play, Data, or Tournaments.
- **Lobby**: Setting up players (Human vs Bots).
- **Game Screen**: Rendering the table and hand, and letting you make moves interactively.

### 3. `players/` (The Players)
Contains the `RandomBot` and human player logic tailored for the TUI.

## Getting Started

### How to play
To start the new TUI experience, run this from the root folder:
```bash
python3 -m tui.app
```
*(Note: You'll need the `textual` library installed, which is in the project's `.venv`.)*

### How to run simulations
The simulation runner still works for quick bot-only testing:
```bash
python3 -m tools.run_simulation
```

## Future Plans
My next goal is to move beyond the `RandomBot` and implement something more clever, like a bot that evaluates which cards are most valuable to scout. I might also try to use a simple Minimax algorithm if I have time!

