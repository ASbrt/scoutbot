# Scoutbot
Welcome to my project for ICSS! This project implements a game engine for the card game Scout. It is meant to serve as a basis for exploring Monte Carlo Tree Search and more general ML-based strategy learning.

The long-term goal is to build a system that can:

- simulate large numbers of Scout games
- train stronger AI agents
- generate datasets from gameplay
- explore interpretable strategies learned from simulation

**IMPORTANT:** This is still a work in progress. The project recently underwent a larger refactor from an initial `GameLoop` design to a controller-based architecture in order to support interactive play through a TUI.  
The core engine is functional, and the TUI is now working on top of the new architecture, but the project is still under active development.

---

# What is Scout?
Scout is a card game where you cannot reorder your hand. You have to play sets or runs to beat what is currently on the table (**Show**), or take a card from the table to improve your hand (**Scout**). Once per round, you are allowed to do both in one move (**Scout & Show**).

All cards have two values, where only one side is active depending on orientation. At the beginning of each round, players can decide to flip their entire hand once. Afterwards you're only allowed to flip cards when Scouting them from the table. 

The basic rules are simple, but the strategy quickly becomes deeper than it seems.

For a more in depth explanation of how the game works check out this video: https://www.youtube.com/watch?v=Ymb0YsMzP2M

---

# Project Goals

The project serves several purposes:

- build a deterministic simulation engine for Scout
- explore Monte Carlo Tree Search
- experiment with ML approaches for strategy learning
- generate datasets from simulated and human gameplay
- investigate whether strong AI policies can be distilled into interpretable rule systems

---

# Getting Started

## 1. Install dependencies

It is recommended to use a virtual environment.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
## 2. Start the TUI from project root directory

```bash
python3 -m tui.app
```

This starts the current Textual-based interface, where you can configure a game in the setup screen and then play against bots.

You can quit the UI with Ctrl+Q.

---

# Current Status

Implemented:

- controller-based game engine

- playable Textual TUI

- bot play and human interaction flow

- export of gameplay data

Planned next:

- stronger baseline bots

- tournament / evaluation tooling

- Monte Carlo Tree Search agents

- dataset analysis

