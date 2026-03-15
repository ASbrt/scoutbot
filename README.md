# Scoutbot
Welcome to my project for ICSS! This project implements a game engine for the card game **Scout**. This is meant to work as a basis to explore Monte Carlo Tree Searches as well as learn about general ML techniques.

**IMPORTANT:** This is a work in progress! The current implementation needed a bigger refactor from an initial GameLoop design to Controllers to make the TUI work for player input. These classes are implemented now, but not wired in with the TUI yet

## What is Scout?
Scout is a card game where you can't reorder your hand. You have to play sets or runs to beat what's on the table (**Show**), or take a card from the table to improve your hand (**Scout**). Once per round you are allowed to do both in one move. All cards have 2 values on them where only one is active at a time. The basic rules are simple, the strategy is deeper than it seems. 

## How the Code Works 
I've organized the project into several folders to keep things tidy. Here's a breakdown of what each part does:

### 1. `engine/` 
This is where all the game rules live.
- **`engine/state/`**: Definitions for `GameState` and `Card`.
- **`engine/logic/`**: The "referee" code that knows and constructs `legal_moves`.
- **`engine/controllers/`**: Control and advance `GameState` in phases. Split into `RoundController` and `GameController`


### 2. `tui/` 
**WORK IN PROGRESS! Neither finished nor stable!** 

Textual-based interface, currently containing
- **Home Screen**: Navigation to Play, Data (to be implemented), or Tournaments (to be implemented).
- **Lobby**: Setting up players (Human vs Bots).
- **Game Screen**: Rendering the table and hand, and letting you make moves interactively.

### 3. `players/` 
Contains the `RandomBot` and human player logic (to be retired). Will contain more elaborate bots shortly.

## Getting Started

**DONT.** **NOT STABLE RIGHT NOW.** 

If you wanna play anyways:

### How to play
To start the new TUI experience, run this from the root folder:
```bash
python3 -m tui.app
```
*(Note: You'll need the `textual` library installed)

### How to run simulations
The simulation runner still works for quick bot-only testing:
```bash
python3 -m tools.run_simulation
```

## Future Plans
My next goal is to move beyond the `RandomBot` and implement something more clever. I need to finish the TUI first though

