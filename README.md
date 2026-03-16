# Scoutbot
Welcome to my project for ICSS! This project implements a game engine for the card game Scout. This is meant to work as a basis to explore Monte Carlo Tree Searches as well as learn about general ML techniques.

The long-term goal is to build a system that can:

- simulate large numbers of Scout games
- train stronger AI agents
- generate datasets from gameplay
- explore interpretable strategies learned from simulation

**IMPORTANT:** This is a work in progress! The current implementation recently underwent a larger refactor from an initial GameLoop design to Controllers to support interactive play via a TUI.  
The controllers are implemented and the engine is functional, but the TUI is still being wired to the new architecture.

---

# What is Scout?
Scout is a card game where you can't reorder your hand. You have to play sets or runs to beat what's on the table (**Show**), or take a card from the table to improve your hand (**Scout**). Once per round you are allowed to do both in one move (**Scout & Show**).

All cards have **two values**, where only one side is active depending on orientation. At the beginning of each round, players can flip their entire hand.

The basic rules are simple, but the strategy quickly becomes deeper than it seems.

---

# Project Goals

The project serves several purposes:

- build a deterministic simulation engine for Scout
- explore Monte Carlo Tree Search
- experiment with ML approaches for strategy learning
- generate datasets from simulated gameplay
- eventually investigate whether AI policies can be turned into interpretable rule systems

---

# How the Code Works
I've organized the project into several folders to keep things tidy. Here's a breakdown of what each part does.


# 1. `engine/`
This is where all the game rules and state transitions live.  
The engine is designed to be UI-agnostic so it can be used for:

- simulations
- tournaments
- ML training
- interactive play

### `engine/state/`
Defines the core data structures

Main components:

- `CardCore` (containing cards and deck building)
- `GameState` (containing dataclasses for GameState and Move representation)

`GameState` is the single source of truth for the entire game state.  
It contains:

- player hands
- current player
- table state
- scores
- Scout&Show tokens
- round metadata

State transitions are handled functionally. Moves return new state objects rather than mutating the old one.

---

### `engine/logic/`
Contains the rule logic of the game.

Important modules:

- `legal_moves.py` → constructs all legal actions
- `helpers.py` → rule helpers such as
  - `any_empty_hand`
  - `unbeaten_show_cycle`
  - score calculations

This layer acts as the **game referee**.

---

### `engine/controllers/`
Controllers manage the **execution flow** of the game.

The original engine used a monolithic `GameLoop`.  
This was refactored to support **interactive control flow** needed by the TUI.

Controllers now separate **state transitions** from **execution logic**.

Implemented controllers:

#### `RoundController`

Handles one round of Scout in phases:
`CREATED -> FLIP -> TURNS -> FINISHED`


Responsibilities include:

- deck construction and dealing
- flip decisions
- move application
- round termination checks
- score calculation

#### `GameController`

Manages the full game lifecycle:

- round sequencing
- score tracking
- start player rotation
- final game result construction

This architecture allows the same engine to be used for:

- automated simulations
- bot tournaments
- TUI gameplay
- ML data generation

---

# 2. `players/`
Contains **agent implementations**.

Currently implemented:

### `RandomBot`
A simple baseline agent.

Behaviour:

- randomly decides whether to flip its hand
- selects moves randomly
- slightly biased toward **Show** actions if possible to avoid endless scouting loops

Future plans include:

- heuristic rule-based bots
- MCTS-based agents
- policy-based agents trained from simulation data

Human players will eventually be handled **entirely by the TUI**, replacing the previous CLI interface.

---

# 3. `tui/`
**WORK IN PROGRESS! Neither finished nor stable!**

This will provide a **Textual-based interface** for playing and managing simulations.

Planned functionality:

### Home Screen
Navigation to

- Play
- Data / Analysis
- Tournaments

### Lobby
Game configuration:

- number of players
- human vs bot seats
- RNG seed

### Game Screen
Interactive play:

- render player hands
- render table
- navigate possible actions
- execute moves

The TUI interacts with the engine through the **controllers**, allowing:

- human input
- bot turns
- round transitions

---

# 4. `tools/`
Utility modules for **logging, serialization, and simulation tooling**.

### Logging

Game events are logged in structured dataclasses:

GameResult contains RoundResults, which contains a FlipRecord and a TurnRecord per round played.
These logs capture the full decision trajectory of a game.

### Flip Logging
Flip decisions at the beginning of a round are recorded with:

- `hand_before`
- `flip_decision`
- `player_type`

This allows training models to learn **hand orientation decisions**.

### Turn Logging
Each turn records:

- serialized game state
- chosen move
- score changes
- hand size changes
- player metadata

The logs are designed so they can later be **flattened into datasets** for analysis or ML training.

---

# Current Project Status

Working:

- deterministic game engine
- legal move generation
- full round/game controllers
- structured gameplay logging
- simulation runner

In progress:

- wiring controllers into the TUI
- improving bot implementations
- dataset tooling
- analysis utilities

Not yet implemented:

- MCTS agents
- ML training pipeline
- tournament tooling
- visualization tools

---

# Getting Started

**DON'T.**  
**NOT STABLE RIGHT NOW.**

If you want to try things anyway:

### How to play
To start the new TUI experience, run this from the root folder:

```bash
python3 -m tui.app
```

You will need the `textual` library installed.

### How to run simulations
The simulation runner still works for quick bot-only testing:

```bash
python3 -m tools.run_simulation
```

This runs automated games using the engine without the TUI.

---

# Future Plans

Short term:

- finish wiring the controllers into the TUI
- implement stronger baseline bots
- add tournament tooling

Medium term:

- build Monte Carlo Tree Search agents
- generate gameplay datasets
- experiment with ML models trained on gameplay

Long term:

- investigate interpretable strategies derived from AI play
